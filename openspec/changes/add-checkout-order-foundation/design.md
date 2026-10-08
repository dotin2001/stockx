## Context

See `proposal.md` for motivation and the delta specs for behavior. The current FastAPI service persists authenticated carts as user/listing rows and treats `listings.price_cents`, `currency`, `status`, and `available_quantity` as the sellable price and stock source. Cart mutations validate availability but checkout has no transaction, inventory locking, order persistence, or history. The Next.js cart and account surfaces currently reveal a checkout placeholder after the existing guest-to-account cart merge.

The application uses SQLAlchemy 2.x, Alembic, PostgreSQL in development/runtime, integer-cent money, UUID primary keys, thin FastAPI routers, service-layer rules, and protected routes. Most automated service tests use in-memory SQLite, so PostgreSQL-specific row-lock behavior also needs real-database verification.

## Goals / Non-Goals

**Goals:**

- Establish provider-independent order and order-item persistence that can remain stable when Stripe is added.
- Make cart-to-order conversion atomic, idempotent, inventory-safe, and auditable.
- Preserve what the customer reviewed through customer, shipping, catalog, variant, quantity, and money snapshots.
- Provide protected checkout review, confirmation, history, and detail APIs and pages.
- Make unpaid manual confirmation opt-in for development and disabled by default.

**Non-Goals:**

- Stripe SDK/configuration, Checkout Sessions, payment attempts, webhook processing, refunds, or saved payment methods.
- Inventory reservations or expiration, because the only enabled order path in this change confirms a development manual order immediately.
- Customer order cancellation, returns, fulfillment, shipment tracking, confirmation email, or admin order management.
- Discounts, promotional codes, calculated tax, or variable shipping rates.
- Replacing the existing `listings` inventory abstraction.

## Decisions

### Gate manual confirmation with an explicit checkout mode

Add a validated backend setting such as `checkout_mode` with initial values `disabled` and `manual`; default it to `disabled`. The checkout summary remains readable when disabled so the frontend can explain the state, but the order-creation service rejects mutations unless the mode is `manual`. Tests override the setting explicitly, and local documentation explains how to opt in.

Manual mode creates `status = confirmed` and `payment_status = unpaid`. It is suitable for local end-to-end development but is not presented as a paid order. A later Stripe change can add a `stripe` mode that creates `pending_payment` orders without changing the customer order/history contract.

Alternative considered: allow manual confirmation everywhere. That would let an internet-facing deployment consume inventory without collecting payment. Inferring safety from a generic environment name was also rejected because explicit configuration is easier to audit.

### Persist immutable order snapshots alongside nullable source references

Create two tables.

`orders` contains a UUID primary key, non-secret unique public order number, customer `user_id`, customer-scoped idempotency key, normalized request hash, order/payment status, currency, integer-cent subtotal/shipping/tax/total fields, customer name/email snapshots, recipient/contact and shipping-address snapshots, `confirmed_at`, and standard timestamps. Add unique constraints for the order number and `(user_id, idempotency_key)`, checks for known statuses and non-negative money, and `ON DELETE RESTRICT` from orders to users so historical orders are not silently erased.

`order_items` contains a UUID primary key, `order_id`, nullable `listing_id`, `product_id`, and `product_variant_id` source references, product name/slug/image snapshots, variant label/SKU/size/color snapshots, integer-cent unit price and line total, positive quantity, and timestamps. Deleting an order cascades to its items; deleting or replacing a source record sets its item reference to null while leaving snapshots intact.

The initial status checks include `pending_payment`, `confirmed`, and `cancelled`; payment states include `unpaid`, `paid`, `failed`, and `refunded`. Only `confirmed` plus `unpaid` is created by this change. The additional values define the intended Stripe seam but do not expose unsupported transitions.

Alternative considered: render history by joining live product/listing data. That would rewrite past names, variants, prices, and potentially make old orders unreadable after deletion. A single JSON order snapshot was also rejected because relational items are easier to validate, paginate, and extend.

### Expose a checkout summary separately from order creation

Add protected `GET /api/v1/checkout/summary`, `POST /api/v1/orders`, `GET /api/v1/orders`, and `GET /api/v1/orders/{order_id}` endpoints. Keep route handlers thin and put calculation, locking, validation, creation, and serialization in checkout/order services.

The summary returns normalized line data, one currency, subtotal, explicit zero shipping and tax, total, checkout mode/availability, and an opaque checkout token. The token is a keyed digest over the customer and deterministically ordered current cart/listing state, including cart row, listing, quantity, unit price, currency, listing status, available quantity, and product archive state. Order creation recomputes the digest after acquiring locks and returns a conflict when it differs, forcing the customer to review changes rather than silently accepting them.

`POST /orders` accepts only the checkout token and normalized customer/shipping fields in the JSON body plus a required `Idempotency-Key` header. It never accepts authoritative product lines, quantities, unit prices, or totals. Shipping and tax remain zero in this foundation and are stored explicitly rather than omitted.

Alternative considered: create orders directly from the values displayed by the frontend. That trusts stale or manipulated data. Folding summary and creation into one call was rejected because the customer needs a stable review boundary and change detection.

### Serialize checkout per customer and lock shared inventory deterministically

Order creation uses one database transaction and follows this order:

1. Reject disabled checkout before mutation.
2. Lock the current user row, then look up an existing order for the idempotency key.
3. Return the existing order for the same normalized request hash, or reject a reused key with different request data.
4. Lock the user's cart rows and load associated products/variants.
5. Lock all referenced listing rows in stable identifier order to avoid cross-customer deadlocks.
6. Revalidate non-empty cart, product archive state, listing status, available quantity, single currency, and checkout token.
7. Compute authoritative money, create the order and snapshot items, decrement listing quantities, and delete the purchased cart rows.
8. Flush and commit once in the route; any failure rolls back the entire unit.

Existing add/update/remove/merge cart mutations should acquire the same customer-row lock before changing an authenticated cart. This prevents a concurrent cart insert or quantity change from escaping the checkout snapshot boundary. The database unique constraint remains the final idempotency safeguard.

Listings that reach quantity zero remain `active` with zero availability; existing public/cart rules already exclude them. Automatically switching to `sold` would mix quantity management with a status lifecycle that admins currently control.

Alternative considered: check availability and decrement without row locks. Two customers could then purchase the same final unit. Serializable isolation for every API transaction was rejected as broader and more expensive than targeted locks.

### Keep history access user-scoped and read-only

List orders newest first with the project's limit/offset pagination pattern. Detail queries filter by both order ID and current user ID and return not found for cross-user access. The public order number is for display only and never replaces authorization. No customer mutation route is added.

Alternative considered: expose order lookup by public number alone. Even with randomized numbers, that creates unnecessary disclosure risk and weaker authorization semantics.

### Add dedicated protected frontend routes

Add `/checkout`, `/orders`, and `/orders/[id]` using the existing auth provider and protected-gate pattern. Guest Checkout continues to redirect through login/signup, but its return target becomes `/checkout` so the existing guest cart is merged before summary load.

The checkout page renders server data, shipping fields, disabled/manual messaging, validation conflicts, and a single-submit state. It generates and retains one idempotency key per confirmation attempt. Success routes to `/orders/[id]?created=1`; the same detail page supplies both immediate confirmation and later history. The account surface links to order history and stops duplicating the cart checkout placeholder.

Alternative considered: keep checkout and orders embedded in the account dashboard. Dedicated routes produce clearer loading/error boundaries and map cleanly to the later Stripe redirect flow.

### Keep payment-provider state outside the order foundation

Do not add Stripe identifiers or generic payment-attempt rows to `orders`. The later Stripe change should add a related payment-attempt table and webhook-event deduplication while using the existing order ID as reconciliation metadata. This keeps historical order records provider-independent and supports more than one payment attempt per order.

Alternative considered: add a nullable Stripe Checkout Session ID directly to orders now. That couples the domain to a provider before payments exist and cannot represent retries cleanly.

## Risks / Trade-offs

- Development manual orders permanently consume inventory while remaining unpaid -> Default checkout to disabled, require explicit local opt-in, label payment state clearly, and keep production payment integration separate.
- SQLite tests do not exercise PostgreSQL row locking -> Keep fast functional tests, and add a real-PostgreSQL concurrency verification for final-unit competition plus migration apply/rollback checks.
- Updating existing cart mutations to participate in the customer lock broadens the backend touch surface -> Centralize the lock helper and add regression tests for add, update, remove, and guest merge behavior.
- A secret rotation invalidates an open checkout token -> Treat that as a safe conflict and ask the customer to refresh the summary.
- External image URLs copied into order snapshots can later become unavailable -> Preserve the original URL for historical context; owned image storage remains separate future work.
- Order downgrade would delete order data -> Disable checkout first and require backup or confirmation that no retained order data is needed before downgrading past the migration.

## Migration Plan

1. Add the deterministic Alembic migration, SQLAlchemy relationships, and database-foundation tests for `orders` and `order_items` while checkout remains disabled.
2. Add configuration, schemas, checkout/order services, routes, error contracts, and backend tests; keep the default mode disabled.
3. Update cart mutations to use the shared customer lock and verify existing cart/guest-merge behavior remains intact.
4. Add frontend types, API methods, routes, forms, confirmation/history UI, and cart/account navigation changes.
5. Update backend documentation and smoke tooling; opt into manual mode only in the local test environment and run migration, backend, PostgreSQL concurrency, smoke, frontend lint, typecheck, and build checks.
6. Roll back by disabling checkout and reverting frontend routes/services first. Downgrade the database migration only when dropping retained development order data is acceptable.
