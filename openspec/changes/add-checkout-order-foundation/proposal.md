## Why

The storefront already supports guest and authenticated carts, but authenticated checkout still stops at a placeholder and there is no durable record of a customer's purchase intent. A provider-independent order foundation is needed now so checkout confirmation and order history can be built before Stripe payment processing is introduced.

## What Changes

- Add durable `orders` and `order_items` records with customer, shipping-address, money, status, and immutable catalog/variant/price snapshots.
- Add an authenticated checkout summary and an idempotent order-creation flow that revalidates the current cart, updates listing inventory, clears purchased cart rows, and creates the order atomically.
- Keep guest checkout authentication-gated and preserve the existing guest-to-account cart merge behavior.
- Allow explicit manual checkout only when a development configuration enables it; keep order placement disabled by default so deployments cannot accept unpaid production orders accidentally.
- Add authenticated customer order confirmation, paginated order history, and user-scoped order detail experiences.
- Extend running-service smoke coverage for checkout and order history.
- Defer Stripe Checkout Sessions, payment attempts, webhooks, refunds, fulfillment, shipment tracking, and admin order management to later changes.

## Capabilities

### New Capabilities

- `checkout-order-creation`: Defines authenticated checkout summaries and safe, idempotent conversion of a cart into a development-only manual order.
- `customer-order-history`: Defines order confirmation, customer-scoped order listing, and immutable historical order detail.

### Modified Capabilities

- `api-smoke-testing`: Extends the running-service smoke workflow to cover manual checkout order creation and customer order retrieval when development checkout is enabled.

## Impact

- Database: new PostgreSQL tables, constraints, relationships, and an Alembic migration for orders and immutable order item snapshots.
- Backend: new order models, Pydantic schemas, checkout/order services, authenticated API routes, configuration, consistent errors, tests, and smoke coverage.
- Frontend: new `/checkout`, `/orders`, and `/orders/[id]` routes; API types/client methods; cart and account navigation updates; checkout loading, disabled, validation, success, empty, and error states.
- Inventory: `listings.available_quantity` remains the authoritative stock value and is decremented only inside the successful order transaction.
- Payments: no Stripe SDK, secrets, sessions, webhooks, or payment collection are introduced by this change.
