## Context

The current FastAPI backend has thin routers, service modules, SQLAlchemy models, Alembic migrations, and tests for auth, catalog, admin product management, listings, watchlist, and cart. Listings already store a `status` constrained to `active`, `sold`, or `cancelled`; products already have archive metadata; cart and watchlist tables already have uniqueness constraints for user-scoped duplicate prevention.

The hardening work spans listing service behavior, admin routes, cart/watchlist/admin product conflict handling, a backend command entry point, tests, smoke coverage, and docs. See `proposal.md` and the delta specs for the behavior contract.

## Goals / Non-Goals

**Goals:**

- Keep route handlers thin and push business rules into services.
- Reuse existing listing status values and product archive metadata.
- Convert expected database integrity races into stable API errors.
- Add a simple operator-facing admin promotion command without expanding the authentication model.
- Preserve existing API response shapes unless the new listing management routes require additional read schemas.

**Non-Goals:**

- No checkout, order, payment, inventory reservation, or purchase flow.
- No product hard delete behavior.
- No admin role hierarchy beyond `users.is_admin`.
- No self-service admin signup endpoint.
- No broad database redesign unless implementation reveals a missing constraint needed to satisfy the specs.

## Decisions

### Use listing status transitions instead of deleting listings

Seller and admin cancellation should set `listings.status = "cancelled"` and keep the record. This matches the existing status constraint and keeps cart/watchlist/history references explainable.

Alternative considered: delete cancelled listings. That would remove useful marketplace history and could cascade into cart rows because `cart_items.listing_id` uses `ON DELETE CASCADE`.

### Add seller listing read/cancel routes under `/api/v1/listings`

Use the existing protected listing router for seller-owned operations:

- `GET /api/v1/listings`
- `POST /api/v1/listings/{listing_id}/cancel`

The service should always scope seller reads and cancellation by `user_id`. Cross-user cancellation should return not-found or equivalent non-disclosing rejection.

Alternative considered: add `/api/v1/account/listings`. The project already has a listing router, so extending it keeps the API surface smaller for this foundation.

### Add admin listing management under `/api/v1/admin/listings`

Use the existing admin router and admin dependency for managed listing views and cancellation:

- `GET /api/v1/admin/listings`
- `POST /api/v1/admin/listings/{listing_id}/cancel`

The managed listing read model should include listing id, owner id, product summary, optional variant id, price, currency, status, and timestamps. Filters should start conservative: `status`, `limit`, and `offset`.

Alternative considered: reuse seller routes with admin behavior. Separate admin routes keep authorization and response shape explicit.

### Enforce product availability in listing creation

Listing creation should load the product and reject archived products before creating a listing. The error code should be stable, such as `product_archived`, and should use the existing API error response shape.

Alternative considered: allow listings for archived products and rely on public catalog/cart filtering. That leaves a confusing seller experience and creates listings for products customers cannot browse.

### Handle uniqueness races at service boundaries

The service layer should keep user-friendly preflight checks for duplicate slugs, cart rows, and watchlist rows, but also catch expected `IntegrityError` failures at flush/commit boundaries and translate them into stable API errors.

For cart duplicate add, prefer resolving into a merged cart item when practical:

1. Attempt to create or update.
2. If a user/listing unique constraint race occurs, roll back the failed unit of work as needed.
3. Re-load the existing cart item, apply the intended quantity merge, and return the cart item.

For product slug and watchlist duplicate conflicts, return conflict errors rather than retrying with changed data.

Alternative considered: use Postgres-specific upsert for all duplicate paths. That is efficient but makes SQLite-based tests less representative unless the project adds separate dialect-specific test coverage. Catching expected integrity failures keeps the first hardening pass portable.

### Add an admin bootstrap command as a Python module and console script

Add a small backend command that promotes an existing user by normalized email. A module entry point like `python -m app.admin promote user@example.com` should work even before packaging, and a console script can be added for installed environments.

The command should not create users, read passwords, or modify refresh tokens. It should return a non-zero process exit for missing users or database errors.

Alternative considered: seed a default admin account. That risks checked-in credentials or environment coupling. Promoting an existing user is safer and fits the current auth flow.

## Risks / Trade-offs

- Integrity error handling can accidentally catch too much -> inspect constraint names or columns where possible and re-raise unknown integrity failures.
- SQLite tests may not expose the same constraint metadata as PostgreSQL -> cover service behavior with SQLite tests and keep Postgres migration/seed/smoke verification in the workflow.
- Cancelling a listing already in carts will leave cart rows visible but unavailable -> this is consistent with current cart availability behavior and should be covered by tests.
- Admin listing reads could grow into a moderation dashboard -> keep filters minimal in this change and defer search/sort expansions.

## Migration Plan

No schema migration is expected. If implementation discovers a required database constraint or index, add a deterministic Alembic migration and verify apply/rollback against local PostgreSQL.

Implementation should be deployable in-place:

1. Add service and route behavior.
2. Add command entry point.
3. Run tests.
4. Run migrations only if a migration was added.
5. Run seed idempotency and smoke coverage.

Rollback is code rollback only unless a migration is introduced. If a migration is introduced, rollback must include `alembic downgrade -1` verification.
