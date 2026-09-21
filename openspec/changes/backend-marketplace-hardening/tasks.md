## 1. Listing Management

- [x] 1.1 Add listing read schemas for seller and admin management views, and verify schema serialization includes listing id, owner id, product data, price, currency, status, and timestamps.
- [x] 1.2 Update listing creation service behavior to reject archived products with a stable API error, and verify API tests cover active product success, missing product rejection, and archived product rejection.
- [x] 1.3 Implement seller listing list behavior scoped to the current user, and verify API tests prove users only see their own listings and anonymous clients receive authentication errors.
- [x] 1.4 Implement seller listing cancellation by setting owned active listings to `cancelled`, and verify API tests cover successful cancellation, cross-user rejection, missing listing rejection, and already-cancelled idempotency.
- [x] 1.5 Implement admin listing list behavior with status, limit, and offset filters, and verify API tests cover admin success plus non-admin and anonymous rejection.
- [x] 1.6 Implement admin listing cancellation without deleting listing records, and verify API tests cover admin cancelling another user's active listing plus non-admin and anonymous rejection.

## 2. Marketplace Write Integrity

- [x] 2.1 Add a narrow integrity-conflict handling approach for expected unique constraint failures, and verify unknown integrity failures are not silently converted into misleading marketplace errors.
- [x] 2.2 Harden admin product create/update slug conflicts at database flush or commit boundaries, and verify tests cover duplicate slug preflight and simulated or real database uniqueness conflict behavior.
- [x] 2.3 Harden cart duplicate user/listing add behavior so retries or uniqueness races keep one cart row, and verify tests cover duplicate merge, cross-user cart independence, and handled integrity conflict shape.
- [x] 2.4 Harden watchlist duplicate user/product add behavior at database flush or commit boundaries, and verify tests cover duplicate conflict responses and no duplicate row creation.
- [x] 2.5 Verify all handled uniqueness conflicts use the standard `{"error": {"code": ..., "message": ...}}` response shape without raw SQL or driver exception text.

## 3. Admin Bootstrap

- [x] 3.1 Add an admin promotion service that normalizes email and promotes an existing user, and verify service tests cover non-admin promotion, already-admin idempotency, and missing user failure.
- [x] 3.2 Add a module command entry point for admin promotion, and verify `python -m app.admin promote <email>` exits successfully for an existing user and non-zero for a missing user.
- [x] 3.3 Add an installed console script for admin promotion if package metadata supports it cleanly, and verify the command invokes the same promotion behavior as the module entry point.
- [x] 3.4 Verify admin promotion does not create users, request passwords, alter password hashes, or revoke refresh tokens.

## 4. Documentation and Smoke Coverage

- [x] 4.1 Update `apps/api/README.md` with seller listing management, admin listing management, and admin bootstrap command documentation, and verify documented routes match implemented router paths.
- [x] 4.2 Extend running-service smoke coverage for seller listing list/cancel behavior and archived-product listing rejection, and verify the smoke command passes against local PostgreSQL with migrations and seed data applied.
- [x] 4.3 Extend smoke or focused command coverage for admin promotion in a safe local-only flow, and verify the promoted user can access an admin-only endpoint.

## 5. Verification

- [x] 5.1 Run the backend test suite from `apps/api`, and verify `pytest` passes.
- [x] 5.2 If no migration was added, verify `alembic current` reports the expected head; if a migration was added, verify `alembic upgrade head`, `alembic downgrade -1`, and re-upgrade complete successfully.
- [x] 5.3 Run seed data twice after implementation, and verify `python -m app.db.seed` remains idempotent.
- [x] 5.4 Run `openspec validate backend-marketplace-hardening --strict`, and verify the change remains valid after implementation updates.
