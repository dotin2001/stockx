## Context

See `proposal.md` for motivation and the delta specs for required behavior. The application already stores immutable order, order-item, customer, shipping, money, reservation, and safe payment-attempt state. Customer `GET /api/v1/orders` and `GET /api/v1/orders/{id}` deliberately filter by the current user's ID, while the admin router uses `CurrentAdminUser` for capabilities shared by normal and supreme admins. The Next.js admin area currently has product, message, and supreme-admin user pages but no shared admin shell or order routes.

The existing `OrderRead` contract is safe for authenticated customers: its payment-attempt summaries omit provider session IDs, hosted URLs, webhook payloads, idempotency values, and payment-method data. Its list shape is too large for an admin table because it contains complete shipping and item snapshots. The existing order presentation component also mixes reusable payment labels with customer-only resume and cancellation behavior in the detail client.

This change is read-only and operates on existing rows, so it must preserve current checkout, webhook reconciliation, inventory, customer order scoping, and admin role behavior without a schema migration.

## Goals / Non-Goals

**Goals:**

- Add backend-enforced order visibility for both normal and supreme admins without weakening owner-scoped customer endpoints.
- Keep list payloads bounded and purpose-specific while reusing the existing safe detail serialization.
- Provide deterministic pagination and composable search/status filters with consistent total counts.
- Reuse payment-state presentation without exposing customer payment actions on admin pages.
- Fit existing FastAPI service, Pydantic, Next.js App Router, auth-provider, Tailwind, and smoke-test patterns.

**Non-Goals:**

- Changing order, payment, inventory, reservation, or Stripe webhook state.
- Adding fulfillment, shipment, refunds, disputes, exports, bulk actions, notes, assignment, or customer communication.
- Adding a new admin role or restricting order review to supreme admins.
- Replacing limit/offset pagination or introducing a general admin dashboard framework.
- Adding search infrastructure or a database migration before observed order volume requires it.

## Decisions

### Add separate admin routes and service methods

Add `GET /api/v1/admin/orders` and `GET /api/v1/admin/orders/{order_id}` to the existing admin router, both protected by `CurrentAdminUser`. Put cross-customer queries in a focused admin-order service rather than adding an admin bypass flag to customer order functions. Customer routes continue calling owner-scoped service methods and retain their not-found behavior for cross-user detail.

This makes the authorization boundary visible in routing and service signatures and avoids a boolean such as `include_all_users=True` accidentally reaching customer code. A separate router module was considered, but the existing admin router already owns products, listings, messages, and users; it can include thin order handlers without creating another API prefix.

### Use a dedicated summary contract and the existing safe detail shape

Define an admin order summary and paginated page contract containing identity, customer name/email snapshots, order/payment state, money total, line count, item quantity, latest safe payment-attempt summary, and lifecycle timestamps. The list service loads only a bounded order page with item and payment-attempt relationships using batched eager loading, avoiding per-order queries while keeping the first implementation aligned with existing order loading patterns.

Admin detail reuses `OrderRead` after making the existing serializer an explicit shared service helper. `OrderRead` already contains the complete immutable snapshots required by the spec and excludes sensitive provider fields. Reusing it prevents customer and admin detail representations from drifting.

Returning full `OrderRead` objects from the list was rejected because it would transfer shipping addresses and every item/payment attempt when only summary data is needed. Creating a second complete detail schema was rejected because it would duplicate the established safe contract.

### Normalize all list criteria into one reusable predicate

The list endpoint accepts optional `search`, `status`, and `payment_status` parameters plus the existing bounded `limit` and non-negative `offset`. Trim search input; treat an omitted or whitespace-only value as no search; cap non-empty input at a documented length. Escape SQL wildcard characters before constructing a case-insensitive contains match against `orders.order_number` or the immutable `orders.customer_email` snapshot. Validate statuses against the existing order and payment enums.

Build one combined predicate and apply it to both the total-count query and page query. Supplied search and status criteria use AND semantics; order-number and customer-email matches within the search criterion use OR semantics. Results use `created_at DESC, id DESC` so offset pages are deterministic when timestamps match.

Separate endpoints for each filter were rejected because they complicate composition and pagination. Searching the mutable users table was rejected because admin review must reflect the customer identity snapshot captured by the order.

### Keep the initial query migration-free and measure before indexing

The order table already has durable records and relationships required by this feature. Bounded pages and batched relationship loading are sufficient for the current project scale. Case-insensitive substring matching may scan order rows, so implementation tests should assert query correctness and bounded API limits; production observation should drive a later trigram or functional-index migration if volume makes it necessary.

Adding a speculative PostgreSQL-specific search index now was rejected because it would add migration and extension considerations without measured load. Unbounded list endpoints were rejected because they make response and relationship loading costs unpredictable.

### Build distinct admin clients around shared presentation primitives

Add `/admin/orders` and `/admin/orders/[id]` App Router pages backed by dedicated admin list and detail clients. The list owns URL query state for search, filters, and offset so refresh, back navigation, and copied URLs preserve the review context. Changing a search or filter resets the offset. Each order links to detail with a return query representing the current list state.

The frontend API client gains typed admin list/detail methods and query construction. Reuse money formatting and refactor payment-state presentation to accept the minimal order/payment summary shape shared by customer and admin cards. Extract presentational order snapshot sections only where doing so removes real duplication. Do not reuse the customer detail client itself because it contains Stripe return polling, Resume Payment, and Cancel Pending Order actions that admins must never receive.

One combined admin page with an expanding row was considered, but a dedicated detail route provides a stable support URL, clearer loading/not-found boundaries, and room for future separately proposed operational capabilities.

### Enforce authorization twice without treating frontend gates as security

Desktop and mobile navigation show Orders when `user.is_admin` is true. Admin components wait for auth restoration, then render login-required or admin-required states before requesting data. The API remains authoritative: unauthenticated requests receive authentication errors and authenticated non-admin requests receive authorization errors even if they directly call the endpoint or manipulate frontend state.

Both admin levels use `CurrentAdminUser`; `CurrentSupremeAdminUser` is intentionally not used because prior role design reserves supreme-only authorization for admin-access management. Responses expose immutable customer and shipping snapshots needed for order support but omit provider credentials and internal request data through the safe schemas.

### Extend layered verification without requiring payment mutation

Backend service and API tests cover normal/supreme access, guest/customer rejection, deterministic pagination, empty results, each filter and combined criteria, safe summary/detail serialization, missing detail, and unchanged customer scoping. Frontend source or rendered checks cover desktop/mobile navigation, role gates, URL-backed filters, mixed states, pagination, empty/loading/error/not-found views, detail snapshots, and absence of mutation controls.

The running-service smoke path uses an existing or uniquely created customer order and an operator-provided/bootstrap admin account. It proves the admin can locate and open the order while the customer cannot use the admin endpoints and a different customer still cannot open the customer-owned detail. It does not create refunds, alter Stripe state, or require a new live payment.

## Risks / Trade-offs

- [Substring search becomes slow as order volume grows] -> Keep search input and page size bounded, use deterministic queries, and add an evidence-driven index/search change later.
- [Admin responses expose personal shipping and contact data] -> Require backend admin authorization, return only fields necessary for order review, exclude payment/provider secrets, and avoid client persistence outside normal in-memory rendering.
- [List and detail payment labels drift from customer views] -> Share minimal presentation logic and cover mixed lifecycle states in both frontend paths.
- [Refactoring the serializer regresses customer endpoints] -> Keep the existing `OrderRead` output unchanged and add regression assertions for owner-only list/detail behavior.
- [Offset pagination shifts when new orders arrive] -> Use a stable secondary sort key and accept normal offset behavior for this initial operational view; cursor pagination can be proposed if volume or concurrency demands it.
- [Active Stripe work changes payment-attempt shapes concurrently] -> Build against the safe `PaymentAttemptSummary` contract and avoid provider-specific fields so the admin feature remains compatible with reconciliation changes.

## Migration Plan

1. Add backend schemas, admin-order service queries, routes, and tests while leaving existing customer endpoints unchanged.
2. Extend the running-service smoke workflow and API documentation, then deploy the backend first.
3. Add frontend types/client methods, shared presentation refactor, admin list/detail routes, navigation, and frontend verification.
4. Run backend, frontend, smoke, and strict OpenSpec checks, including explicit customer-scoping regressions.
5. Deploy the frontend after the admin endpoints are available. Roll back the frontend routes/navigation first if needed, then remove the read-only backend routes; no database rollback is required.
