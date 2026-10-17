## Why

The storefront can now turn a cart into a durable development-only unpaid order, but it cannot safely collect money or confirm that a customer paid. The next milestone is a production-oriented Stripe payment path that preserves the existing authoritative checkout, order snapshots, idempotency, and inventory guarantees while making payment confirmation webhook-driven.

## What Changes

- Add an explicit `stripe` checkout mode that uses Stripe-hosted Checkout Sessions for authenticated one-time purchases while retaining disabled-by-default and manual-development behavior.
- Create pending-payment orders and 30-minute inventory reservations before redirecting to Stripe so competing customers cannot pay for the same final unit.
- Add provider-separated payment-attempt persistence that records Checkout Session and PaymentIntent identifiers, amount, currency, lifecycle state, and expiration without coupling provider fields directly to orders.
- Add a signed Stripe webhook endpoint with durable event deduplication, monotonic order/payment transitions, amount and ownership reconciliation, and safe handling of completed, asynchronous success/failure, and expired sessions.
- Confirm orders only from verified paid Stripe state; release reserved inventory exactly once when a pending payment is cancelled, fails terminally, or expires.
- Update checkout, order confirmation, history, and detail experiences for redirect-to-Stripe, payment-pending, paid, expired, cancelled, retry/resume, loading, and error states without treating the browser redirect as payment proof.
- Add Stripe sandbox and CLI documentation plus automated service, PostgreSQL concurrency, webhook, frontend, and running-service smoke coverage.
- Keep automatic tax, paid shipping rates, discounts, saved payment methods, refunds, disputes, Stripe Connect, fulfillment, and customer notifications out of this change.

## Capabilities

### New Capabilities

- `stripe-checkout-payments`: Defines authenticated Stripe Checkout Session creation, pending-order inventory reservation, customer redirect/return behavior, and pending-payment cancellation or expiration.
- `stripe-payment-webhooks`: Defines signed, idempotent Stripe event processing and authoritative order/payment reconciliation.

### Modified Capabilities

- `api-smoke-testing`: Extends running-service smoke coverage to exercise Stripe-mode checkout and verified payment lifecycle behavior in a Stripe sandbox or deterministic provider test harness.

## Impact

- Database: new payment-attempt and Stripe webhook-event tables, order reservation timestamps, deterministic constraints/indexes, and an Alembic migration with safe upgrade/downgrade behavior.
- Backend: Stripe SDK dependency and pinned API version, validated secret/base-URL configuration, checkout-session and pending-order services, signed webhook routing, cancellation/expiration reconciliation, schemas, tests, and smoke tooling.
- Frontend: Stripe-aware checkout submission and hosted redirect, payment return/cancel handling, status polling, and payment lifecycle states in order history/detail.
- Inventory: available listing quantity is reserved when a pending order is created and restored exactly once on terminal unpaid cancellation or expiration; paid confirmation does not decrement it again.
- Operations: Stripe sandbox keys, an endpoint signing secret, Stripe CLI webhook forwarding, enabled instant payment methods, HTTPS webhook registration, and go-live documentation become deployment prerequisites for Stripe mode.
