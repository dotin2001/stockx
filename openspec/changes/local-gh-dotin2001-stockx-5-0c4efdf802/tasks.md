## 1. Application Identity Normalization

- [x] 1.1 Consolidate email canonicalization as trim-plus-lowercase for registration, login, lookup, and non-HTTP callers, reject empty normalized values, and verify focused auth schema/service tests cover canonical storage, lookup, and blank rejection.
- [x] 1.2 Add shared SKU trim-and-blank-to-`NULL` normalization to variant create and update request/service paths, and verify SQLite-compatible tests cover non-empty trimming, blank conversion, omitted update fields, and multiple `NULL` SKUs.
- [x] 1.3 Translate only recognized email and normalized-SKU uniqueness violations into HTTP 409 responses (`email_exists` and one consistent duplicate-SKU code), preserve unknown integrity errors, and verify create/update conflict and rollback tests pass.

## 2. PostgreSQL Integrity Migration

- [x] 2.1 Add an Alembic revision that preflights normalized email collisions, normalized non-empty SKU collisions, and rows incompatible with canonical storage, aborting with actionable errors before schema mutation; verify collision fixtures remain unchanged after each failed upgrade.
- [x] 2.2 Add stable named PostgreSQL enforcement for canonical non-empty emails, normalized email uniqueness, canonical nullable SKUs, and global case-insensitive non-empty SKU uniqueness, then align SQLAlchemy metadata and verify schema inspection sees the expected constraints/indexes.
- [x] 2.3 Implement a non-destructive downgrade for only the new integrity objects and verify upgrade, downgrade, and re-upgrade retain test-owned users, variants, and relationships without rewriting their data.

## 3. Atomic Inventory Adjustments

- [x] 3.1 Replace managed listing quantity read-modify-write logic with a conditional atomic arithmetic update that preserves existing not-found and below-zero API errors, and verify service/API tests cover positive adjustments, valid reductions, missing listings, and rejected underflow.
- [x] 3.2 Add a SQLite-compatible regression test proving sequential adjustments retain the existing response contract and persisted quantity so portable coverage remains intact.

## 4. Guarded PostgreSQL Concurrency Coverage

- [x] 4.1 Introduce a reusable PostgreSQL test guard that clearly skips when `TEST_POSTGRES_DATABASE_URL` is absent, rejects non-PostgreSQL URLs before opening a connection, and verify its configuration tests pass without mutating a database.
- [x] 4.2 Build uniquely tagged PostgreSQL fixtures and foreign-key-safe teardown that track and delete only test-created records, use independent sessions per worker, and use bounded barriers/timeouts; verify an unrelated sentinel record survives teardown.
- [x] 4.3 Add a barrier-coordinated concurrent registration test using equivalent formatted emails and verify exactly one committed user plus one `email_exists` conflict.
- [x] 4.4 Add barrier-coordinated concurrent variant create and update coverage using equivalent SKUs and verify exactly one accepted identity, one consistent duplicate-SKU conflict, and unchanged loser state.
- [x] 4.5 Add barrier-coordinated inventory tests for sufficient and oversubscribed concurrent reductions and verify the committed quantity includes every successful delta exactly once and never becomes negative.

## 5. End-to-End Verification

- [x] 5.1 Run the applicable SQLite backend test suite and verify existing auth, admin product, and inventory behavior remains green.
- [x] 5.2 With an explicitly configured dedicated PostgreSQL test database, run the identity, migration lifecycle, and concurrency suites and verify deterministic outcomes with no whole-database reset or unrelated-record deletion.
- [x] 5.3 Run the repository's backend lint/type checks if configured, full backend tests, and `alembic upgrade head`, downgrade of the new revision, and re-upgrade; record any unavailable tooling or environment prerequisite in the handoff.
