## Context

See `proposal.md` for motivation and the three delta specs for required behavior. The applied checkout foundation already provides authenticated server-calculated summaries, keyed checkout tokens, customer/cart/listing row locks, customer-scoped idempotency, immutable order-item snapshots, integer-cent totals, and customer-scoped order history. It currently has only `disabled` and `manual` modes; manual creation atomically decrements `listings.available_quantity`, clears purchased cart rows, and creates `confirmed` plus `unpaid` orders.

The existing order checks already reserve `pending_payment`, `confirmed`, and `cancelled` status values plus `unpaid`, `paid`, `failed`, and `refunded` payment values, but there is no provider state, reservation expiry, webhook record, background worker, or Stripe dependency. The project uses synchronous FastAPI handlers, SQLAlchemy 2.x, PostgreSQL row locks, Alembic, UUID identifiers, thin routers, Next.js App Router, and browser-held access tokens. The completed `add-checkout-order-foundation` change is an implementation prerequisite and should be archived or otherwise synchronized before this change is archived.

Stripe's current guidance favors Checkout Sessions for one-time on-session payments, requires webhook-based fulfillment rather than trusting the success redirect, and requires idempotent handling because events can be duplicated and arrive out of order. Implementation established Stripe Python `16.0.0` as the latest supported stable SDK and pins client behavior to Stripe API `2026-09-30.endive`.

## Goals / Non-Goals

**Goals:**

- Add a hosted Stripe Checkout path without exposing card data to this application.
- Preserve the existing authoritative checkout-token, snapshot, idempotency, customer-scoping, and PostgreSQL locking guarantees.
- Reserve scarce store inventory before the customer can pay and release it exactly once on a terminal unpaid outcome.
- Make signed provider state, not the browser redirect, authoritative for paid confirmation.
- Keep provider records separate from provider-independent order history and permit later multiple payment attempts per order.
- Make session creation and event reconciliation testable without real network calls while retaining a real Stripe sandbox/CLI smoke path.

**Non-Goals:**

- Embedded or custom Checkout UI, raw PaymentIntents, Payment Links, saved payment methods, subscriptions, or Stripe Connect.
- Automatic tax, non-zero shipping rates, promotions, currency conversion, or customer-adjustable quantities in Stripe.
- Refunds, disputes, chargebacks, fulfillment, shipment tracking, admin order management, or customer email.
- A general job-queue platform; reconciliation is limited to short synchronous transitions plus a focused recovery command.
- Automatically rebuilding an expired customer's cart after a normal abandoned session; only a provider-creation failure before redirect is compensated back into the cart.

## Decisions

### Use Stripe-hosted Checkout Sessions behind a provider adapter

Add `stripe` to `CheckoutMode` and a small payment-provider boundary used by the checkout and reconciliation services. The production adapter creates, retrieves, and expires Stripe Checkout Sessions through the official Python SDK; tests use a deterministic fake implementing the same application-facing contract. Do not introduce a generic multi-provider abstraction beyond the operations required by this change.

Create sessions in `payment` mode with dynamic payment methods controlled in the Stripe Dashboard rather than hardcoding `payment_method_types`. The initial operational checklist enables only instant methods such as cards and compatible wallets. The webhook path still handles asynchronous success/failure defensively if an account later enables a delayed method. Use inline server-derived `price_data` from immutable order snapshots rather than trusting client values or requiring a Stripe Price object for every inventory listing.

Alternative considered: a custom Payment Element backed by a raw PaymentIntent. It adds client-secret handling and payment-form complexity without improving the initial store checkout. Payment Links cannot carry the required atomic local reservation and customer-scoped order lifecycle.

### Add provider-separated payment and event persistence

Create `payment_attempts` with a UUID primary key; required order relationship; provider and lifecycle status; integer-cent amount and three-letter currency; provider Checkout Session and PaymentIntent identifiers; provider environment; hosted URL; provider idempotency key; expiration, completion, and failure fields; and timestamps. Provider session and PaymentIntent identifiers are unique when present. The schema permits multiple attempts per order, while the initial service returns the current open attempt and does not create a second active attempt concurrently.

Create `stripe_webhook_events` with a UUID primary key; unique Stripe event ID; event type; provider object ID; livemode; processing status; safe error summary; payload digest rather than a full payload; received/processed timestamps; and standard timestamps. Failed events can be recovered by event ID from Stripe rather than retaining card-adjacent webhook payloads.

Add nullable `reservation_expires_at` and `inventory_released_at` to orders. Existing manual orders remain unchanged with null reservation fields. `inventory_released_at` is the durable exactly-once marker used with the terminal order state under row lock.

Alternative considered: nullable Stripe columns directly on `orders`. That cannot represent retries cleanly and couples historical orders to one provider. Storing complete webhook JSON was rejected because event IDs plus retrieval are sufficient for recovery and reduce sensitive-data retention.

### Reserve inventory in a local transaction before the provider call

`POST /api/v1/checkout/sessions` reuses the existing lock order: customer, cart rows, then sorted listing rows. It revalidates the checkout token and authoritative totals, then atomically creates a `pending_payment`/`unpaid` order and snapshot items, creates an `initializing` payment attempt, sets a 30-minute reservation expiry, decrements listing availability, and deletes purchased cart rows. The route commits this local reservation before calling Stripe so database locks are never held across a network request.

After commit, create the Checkout Session with a provider idempotency key derived from the payment-attempt UUID and attach `order_id`, `payment_attempt_id`, and a non-secret correlation value in metadata/client reference fields. The session uses the same 30-minute expiration and success/cancel URLs built only from validated `FRONTEND_BASE_URL`. A second short transaction records the session ID, optional PaymentIntent ID, hosted URL, environment, expiration, and `open` state.

If Stripe definitively rejects creation, a compensation transaction locks the customer, order, attempt, and referenced listings; marks the order cancelled and attempt failed; restores inventory once; and upserts the removed cart quantities. If the result is ambiguous, leave the attempt `initializing` and retry the same provider idempotency key. The response never exposes a URL until the provider session is durably attached.

Alternative considered: hold listing locks while calling Stripe. That avoids compensation but lets provider latency or outages block cart and inventory transactions. Creating the provider session before any local record was also rejected because crash recovery and metadata correlation become unreliable.

### Reuse customer idempotency and add recovery for incomplete initiation

Keep the current normalized request hash and `(user_id, idempotency_key)` uniqueness on orders. Equivalent retries load the existing order and current payment attempt. An `open` attempt returns its stored hosted URL; an `initializing` attempt retries the same Stripe operation; a conflicting request hash is rejected.

Add a focused reconciliation command that scans stale `initializing` attempts and locally expired pending reservations. For an initializing attempt it repeats the same idempotent session creation or compensates only after a definitive provider result. For an expired reservation it retrieves the provider session before deciding: paid state confirms, asynchronous processing stays reserved, and expired/unpaid state releases. Deployments run this command periodically; request-time reads may also invoke reconciliation for the one requested order but are not the only cleanup mechanism.

Alternative considered: introduce Celery/Redis and an outbox now. That is a larger operational platform than this payment milestone needs. The persisted attempt state and recovery command leave a clean path to move the same jobs to a queue later.

### Make webhook reconciliation the authoritative state machine

Expose `POST /api/v1/payments/stripe/webhook` outside customer authentication. Read the raw body, verify `Stripe-Signature` with the configured endpoint secret and official SDK, and parse only after verification. Handle snapshot Checkout events for `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed`, and `checkout.session.expired`; acknowledge other valid signed types without business mutation.

For a supported event, retrieve the current Checkout Session when needed, resolve the local attempt from its unique session ID or trusted metadata, and verify event/session livemode, order/attempt IDs, amount, currency, and provider state. Insert the event ID and apply the transition in a short transaction that locks the attempt, order, and listing rows. A unique event constraint catches concurrent duplicate delivery, while monotonic state guards make distinct duplicate or out-of-order events harmless.

Transitions are:

- verified `paid` -> attempt `paid`, order `confirmed`/`paid`, set `confirmed_at`, retain consumed reservation;
- completed but unpaid/processing -> attempt `processing`, order stays `pending_payment`/`unpaid`, reservation remains;
- verified asynchronous failure or expired/unpaid -> attempt terminal, order `cancelled`/`failed`, restore inventory once;
- terminal paid order -> ignore later failure/expiry for business state;
- mismatch or unknown correlation -> persist a failed/anomalous event outcome, do not mutate the order, and surface it operationally.

Return success only after durable handling of valid permanent outcomes. Invalid signatures return a client error. Transient database/provider failures return a retryable server error so Stripe retries. No email, fulfillment, or other slow external work runs in the webhook request; a future queue can take those concerns.

Alternative considered: trust the success redirect or client session ID to confirm payment. Customers might never reach that page, query parameters are forgeable, and delayed methods complete later, so it cannot be authoritative.

### Treat cancellation as provider reconciliation, not a local toggle

An owner-scoped cancellation endpoint operates only on `pending_payment` orders. It retrieves the current Stripe session, expires it if still open, then runs the same row-locked terminal reconciliation used by webhooks. If Stripe already reports paid, paid confirmation wins. Replaying cancellation returns the existing terminal state without restoring inventory again.

The Stripe `cancel_url` only returns the customer to their order detail; it does not itself cancel the local order because leaving the hosted page does not close the Checkout Session. The detail page offers Resume Payment while the stored session is open and Cancel Pending Order as an explicit action. A normally expired or cancelled order does not silently rebuild the cart; the customer can return to the product/catalog. A definitive session-creation failure before redirect does restore the original cart because the customer never obtained a payment path.

Alternative considered: cancel automatically when Stripe sends the browser to `cancel_url`. That would trust a browser navigation for a provider-side state transition and could race with a payment completed in another tab.

### Extend order APIs and frontend states without exposing provider secrets

Add these API surfaces under `/api/v1`:

- authenticated `POST /checkout/sessions` with the existing checkout-token/shipping body and required `Idempotency-Key`;
- authenticated `GET /orders/{order_id}/payment-session` returning only owner-visible status and an open resumable hosted URL;
- authenticated `POST /orders/{order_id}/cancel-payment` for pending unpaid orders;
- public signed `POST /payments/stripe/webhook`;
- an operational reconciliation command, not a public unauthenticated retry endpoint.

Extend order responses with reservation expiry and safe payment-attempt summary fields, but keep provider secrets and raw events out. Order list/detail remain filtered by current user. Do not put the Stripe secret key, webhook secret, or Checkout Session URL in logs; the hosted URL is returned only to the owning authenticated customer while open.

The checkout page selects copy and behavior from server checkout mode. Stripe mode submits once, receives a URL, and uses full-page navigation to hosted Checkout. Success returns to `/orders/{id}?payment=return&session_id={CHECKOUT_SESSION_ID}` and cancel returns to `/orders/{id}?payment=cancelled`; query values only influence explanatory UI. The detail page polls authenticated order state for a bounded period after return and presents pending, processing, paid, failed, expired, and cancelled states. History cards stop assuming every order is confirmed/unpaid.

Alternative considered: expose a frontend publishable key and embed Stripe.js immediately. Hosted redirect does not need either and minimizes frontend/payment surface area.

### Keep shipping, tax, and Stripe customer scope intentionally narrow

Continue collecting and validating the shipping snapshot in the application before Stripe redirect. Send the authenticated account email to Checkout for convenience, but do not create or persist a Stripe Customer in this change. Shipping and tax stay explicit zero values and are included in reconciliation; Stripe automatic tax and shipping-rate selection remain disabled. Checkout does not allow quantity adjustment.

Alternative considered: let Stripe own shipping address and tax now. That would change the established pre-payment review contract and introduce tax/address reconciliation beyond the payment milestone.

### Validate configuration and use separate test/live secrets

Add secret key, webhook secret, frontend base URL, reservation duration, and expected Stripe livemode settings. `disabled` and `manual` modes do not require Stripe secrets. `stripe` mode fails configuration validation unless all required values are present, the base URL is absolute and allowed for the environment, and the reservation duration is the supported 30 minutes. Keep secrets server-side and document distinct endpoint secrets for Stripe CLI, sandbox, and live destinations.

Use the latest supported SDK with an explicitly pinned Stripe API version. Register only required Checkout event types. Dashboard configuration controls available payment methods; the first rollout enables instant methods only.

Alternative considered: infer provider readiness from whether one key happens to exist. Explicit mode-aware validation prevents partially configured deployments from accepting checkout.

## Risks / Trade-offs

- Provider calls occur after a committed local reservation -> Persist `initializing` attempts, use stable Stripe idempotency, compensate definitive failures, and run periodic reconciliation for ambiguous or interrupted attempts.
- Abandoned Checkout temporarily hides stock -> Limit open reservations to 30 minutes and reconcile `checkout.session.expired` plus locally overdue attempts.
- Stripe webhooks can be duplicated, delayed, or reordered -> Store unique event IDs, retrieve current provider state when necessary, lock rows, and enforce monotonic transitions with an exactly-once release marker.
- Paid and cancellation/expiry processing can race -> Recheck provider state and serialize transitions on the payment attempt and order; verified paid state wins and inventory is never released afterward.
- Unexpected delayed payment methods can exceed the normal reservation window -> Enable instant methods only initially and keep an unexpectedly processing attempt reserved until its signed terminal event.
- Synchronous webhook transactions could time out under future load -> Keep handlers limited to signature verification and one short reconciliation transaction; move side effects to a queue before adding email, fulfillment, or high volume.
- Hosted Checkout URLs can authorize entry into a payment session -> Return them only to the owning authenticated customer, avoid logs, and expire the provider session on explicit cancellation.
- Downgrading payment tables can erase reconciliation history while sessions remain payable -> Disable Stripe checkout, keep webhook handling active, drain or expire all pending attempts, back up data, and only then downgrade.

## Migration Plan

1. Archive or synchronize the completed checkout/order foundation so its order and checkout contracts are the stable prerequisite for this change.
2. Add the Stripe SDK/configuration and a deterministic migration for order reservation fields, `payment_attempts`, and `stripe_webhook_events`; keep checkout mode disabled and verify upgrade/downgrade against PostgreSQL.
3. Add the provider adapter, pending-order reservation/compensation service, session endpoints, recovery command, schemas, and unit/PostgreSQL concurrency tests while Stripe mode remains disabled.
4. Add raw-body signature verification, event persistence, reconciliation state machine, cancellation behavior, and duplicate/out-of-order/race tests.
5. Update the Next.js checkout, order detail, and history states plus source/browser tests.
6. Configure Stripe sandbox credentials and a CLI-forwarded webhook secret, enable only instant sandbox methods, run the full paid/expired/duplicate smoke flows, and verify inventory and customer scoping.
7. Deploy the migration and backend first with Stripe mode disabled, register the HTTPS webhook destination and required events, deploy the frontend, run sandbox verification, then explicitly enable Stripe mode.
8. For rollback, disable new session creation first but keep webhook and reconciliation processing online until every open or processing attempt becomes paid or terminal. Revert frontend payment entry points next; retain tables and provider processing until no payable sessions remain.
