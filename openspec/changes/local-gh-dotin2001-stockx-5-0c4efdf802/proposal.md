## Why

Email and SKU identity currently relies partly on application prechecks and exact stored strings, so concurrent writes and formatting differences can bypass the intended uniqueness rules. PostgreSQL-backed concurrency coverage is also needed to prove identity conflicts and inventory reductions remain safe under real transactional behavior.

## What Changes

- Normalize account emails as trimmed lowercase values, reject empty normalized emails, and enforce normalized uniqueness in PostgreSQL while preserving the existing `409 email_exists` API contract.
- Normalize variant SKUs by trimming them and storing blank values as `NULL`; enforce global case- and surrounding-whitespace-insensitive uniqueness for non-empty SKUs and return a stable duplicate-SKU conflict from variant create and update operations.
- Add collision-detecting, reversible migration behavior that refuses to add the constraints when existing normalized identities conflict, without merging, renaming, deleting, or otherwise rewriting business records.
- Make inventory reductions concurrency-safe so overlapping requests cannot produce negative inventory or silently overwrite a successful adjustment.
- Add deterministic PostgreSQL tests with independent connections and synchronization barriers for concurrent email registration, equivalent SKU submissions, and inventory reductions, while retaining applicable SQLite coverage.
- Require PostgreSQL-only tests to use `TEST_POSTGRES_DATABASE_URL`, skip clearly when it is absent, reject non-PostgreSQL URLs, isolate their records, and verify migration upgrade, downgrade, and re-upgrade.

## Capabilities

### New Capabilities

- `normalized-identity-integrity`: Defines canonical email and SKU storage, database-enforced uniqueness, collision-safe migration behavior, and stable API conflicts under concurrent writes.
- `inventory-adjustment-concurrency`: Defines atomic inventory reductions and deterministic PostgreSQL concurrency verification that prevents negative quantities and lost updates.

### Modified Capabilities

- None.

## Impact

- Affects FastAPI auth and admin product-variant services, Pydantic request normalization, SQLAlchemy user and product-variant models, integrity-error translation, and listing inventory adjustment logic.
- Adds an Alembic migration with PostgreSQL normalization/uniqueness constraints or indexes and explicit preflight collision checks, with a non-destructive downgrade.
- Extends backend unit/integration coverage and PostgreSQL-only concurrency and migration tests; no frontend behavior or public route shape changes are planned.
