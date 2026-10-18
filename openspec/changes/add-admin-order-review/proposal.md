## Why

Store admins can manage catalog, inventory, and customer messages, but they cannot review the orders customers have placed. Now that durable customer orders and verified Stripe payment states exist, admins need a secure read-only surface for support and operational visibility without using a customer's account.

## What Changes

- Add normal-admin and supreme-admin access to a paginated list of all customer orders, ordered newest first.
- Add admin order search by exact or partial order number and customer email, plus order-status and payment-status filters.
- Add admin order detail containing customer, immutable item, shipping, money, payment-attempt, and timestamp snapshots.
- Add protected `/api/v1/admin/orders` and `/api/v1/admin/orders/{order_id}` endpoints while preserving the existing customer-scoped order endpoints unchanged.
- Add `/admin/orders` and `/admin/orders/[id]` pages with loading, empty, error, filter, pagination, mixed-payment-state, and not-found experiences.
- Add an Orders link to authenticated admin desktop and mobile navigation.
- Keep this capability read-only: it does not add refunds, fulfillment, shipping updates, customer payment controls, or manual order/payment status changes.
- Extend automated and running-service smoke coverage for admin authorization, customer privacy, filters, pagination, and order snapshots.

## Capabilities

### New Capabilities

- `admin-order-review`: Defines admin-authorized, read-only order list and detail behavior across the API and admin frontend.

### Modified Capabilities

- `api-smoke-testing`: Extends running-service verification to cover admin visibility of customer orders while preserving guest/customer authorization boundaries.

## Impact

- Backend: admin router, order query/serialization service boundaries, Pydantic query/response contracts, authorization tests, and running-service smoke workflow.
- Frontend: admin routes and components, API client and TypeScript types, shared order presentation, responsive admin navigation, and source/rendered-route tests.
- Database: no migration or new persistence is expected; the feature reads existing order, item, shipping, customer, and safe payment-attempt snapshots using bounded paginated queries.
- Security: normal and supreme admins can review every order; guests and customers cannot use the admin endpoints, and customer order endpoints remain owner-scoped.
- Deferred: order mutation, fulfillment, shipment tracking, refunds, disputes, exports, bulk actions, and customer notifications.
