## 1. Database and Configuration Foundation

- [x] 1.1 Add validated `disabled` and `manual` checkout-mode configuration with a disabled default, and verify configuration tests reject unknown values and require explicit manual opt-in.
- [x] 1.2 Add SQLAlchemy `Order` and `OrderItem` models, relationships, status/money constraints, source-reference deletion behavior, snapshot columns, and idempotency uniqueness, and verify database-foundation tests inspect the expected tables, columns, foreign keys, checks, and unique constraints.
- [x] 1.3 Create a deterministic Alembic migration for `orders` and `order_items`, and verify `alembic upgrade head`, schema inspection, and downgrade to the prior revision succeed against local PostgreSQL.
- [x] 1.4 Add stable public order-number and normalized checkout-request hashing helpers, and verify unit tests cover uniqueness/format plus equivalent and conflicting normalized requests.

## 2. Checkout Summary and Cart Synchronization

- [x] 2.1 Add checkout summary and order request/response Pydantic schemas with constrained shipping fields, item snapshots, totals, status values, pagination, and mode availability, and verify schema tests cover valid serialization and invalid shipping input.
- [x] 2.2 Implement authoritative checkout summary calculation, single-currency validation, zero shipping/tax totals, and keyed checkout-token generation, and verify tests cover empty, available, unavailable, quantity-limited, archived-product, mixed-currency, and deterministic-token cases.
- [x] 2.3 Add protected `GET /api/v1/checkout/summary` routing with consistent error responses, and verify API tests cover unauthenticated rejection, disabled-mode review, and enabled-mode summary output.
- [x] 2.4 Centralize the authenticated customer-row lock and make cart add, update, remove, and guest merge acquire it before mutation, and verify existing cart user-scoping, availability, duplicate merge, and guest-merge tests continue to pass.

## 3. Atomic Order Creation

- [x] 3.1 Implement the order-creation service with disabled-mode rejection, customer/cart/listing locks in the designed order, post-lock revalidation, checkout-token comparison, and authoritative total calculation, and verify focused service tests cover each conflict without persistent mutations.
- [x] 3.2 Create customer, shipping, product, variant, quantity, and money snapshots; decrement listing quantities; and delete purchased cart rows in the same transaction, and verify success and forced-failure tests prove full commit or rollback behavior.
- [x] 3.3 Implement customer-scoped idempotency replay and conflicting-key rejection using the database constraint as a final safeguard, and verify duplicate and concurrent retry tests create one order and one inventory decrement.
- [x] 3.4 Add protected `POST /api/v1/orders` with a required `Idempotency-Key` header and thin route-level commit handling, and verify API tests cover missing authentication/key, disabled mode, validation errors, stale checkout, success, replay, and conflicting reuse.
- [x] 3.5 Add a PostgreSQL-backed concurrency test where two customers compete for the final listing unit, and verify exactly one order succeeds, inventory never becomes negative, and the losing cart remains intact.

## 4. Customer Order History API

- [x] 4.1 Implement newest-first customer order listing with limit/offset pagination and snapshot serialization, and verify service tests cover empty, populated, stable ordering, and user-scoped results.
- [x] 4.2 Implement customer-owned order detail lookup that returns not found for missing or cross-user IDs, and verify tests also prove live product, variant, listing, inventory, and account changes do not rewrite historical snapshots.
- [x] 4.3 Add protected `GET /api/v1/orders` and `GET /api/v1/orders/{order_id}` routes, and verify API tests cover authentication, pagination, own-order detail, cross-user nondisclosure, and confirmed-unpaid status output.

## 5. Checkout and Orders Frontend

- [x] 5.1 Add checkout/order TypeScript types and API client methods, including the idempotency header and structured conflict handling, and verify frontend type checking succeeds.
- [x] 5.2 Build the protected `/checkout` route with server summary lines, totals, shipping form validation, disabled/manual mode messaging, stale-summary refresh, stable per-attempt idempotency key, loading, submission, and error states, and verify the route behaves correctly in focused browser smoke checks.
- [x] 5.3 Build protected `/orders` history with newest-first cards, pagination controls, empty/loading/error states, and links to detail, and verify authenticated and empty-history browser states render correctly.
- [x] 5.4 Build protected `/orders/[id]` for both new-order confirmation and historical detail with snapshot items, address, totals, confirmed status, and explicit unpaid messaging, and verify own-order and not-found states render correctly without payment or fulfillment actions.
- [x] 5.5 Replace cart/account checkout placeholders with `/checkout` navigation, change guest authentication return intent to `/checkout`, and add an account order-history entry point, and verify guest cart merge still completes before the protected checkout summary loads.

## 6. Smoke Coverage, Documentation, and Final Verification

- [x] 6.1 Extend the running-service smoke workflow to opt into or require manual checkout, create a unique order from seeded inventory, verify cart clearing/inventory decrement/history/detail, and verify cross-user order access is not disclosed.
- [x] 6.2 Document checkout mode, local manual opt-in, new endpoints, unpaid development semantics, migration safety, and deferred Stripe/payment behavior in backend and frontend documentation, and verify examples match the implemented API contracts.
- [x] 6.3 Run the complete backend test suite and verify all checkout, order, cart regression, auth, catalog, admin, and database-foundation tests pass.
- [x] 6.4 Run PostgreSQL migration apply/downgrade/apply, seed twice, the final-unit concurrency test, and the running-service smoke workflow, and record any environment prerequisite that prevents a check.
- [x] 6.5 Run frontend lint, typecheck, build, and route smoke checks for cart, login return, checkout, order confirmation, order history, and order detail, and verify no existing catalog/account routes regress.
- [x] 6.6 Run `openspec validate add-checkout-order-foundation --strict` and verify the proposal, three delta specs, design, tasks, and implemented behavior remain aligned before handoff.
