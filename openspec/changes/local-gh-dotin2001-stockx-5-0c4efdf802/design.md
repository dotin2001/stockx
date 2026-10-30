## Context

See `proposal.md` for motivation. The API already normalizes registration and login emails in application code, but `users.email` only has an exact unique constraint and registration performs a check before `flush`, leaving a race window. Variant schemas accept raw optional SKUs, `product_variants.sku` has no uniqueness rule, and variant writes do not translate integrity conflicts. Managed inventory adjustment currently reads a listing, computes a Python-side quantity, and then flushes it, so two sessions can overwrite one another. Existing PostgreSQL checkout tests use `TEST_POSTGRES_DATABASE_URL` and independent sessions, but they skip solely on absence and do not uniformly validate the dialect or coordinate every race with a barrier.

The work crosses request validation, services, SQLAlchemy metadata, Alembic, and PostgreSQL integration tests. SQLite remains the default fast-test backend, so portable application behavior must continue to be covered there while PostgreSQL-specific constraint and locking behavior is tested separately.

## Goals / Non-Goals

**Goals:**

- Use one canonicalization rule at request/service boundaries and matching PostgreSQL expressions or constraints.
- Let database constraints arbitrate concurrent identity writes, then translate known constraint failures into stable API errors.
- Apply inventory deltas atomically without serializing unrelated listings.
- Make PostgreSQL race tests deterministic, safe for a shared dedicated test database, and explicit about configuration.
- Keep the migration reversible and refuse ambiguous existing data rather than modifying it automatically.

**Non-Goals:**

- Expanding email validation beyond the existing API contract or adding mailbox verification.
- Changing existing endpoint paths, authorization policy, or response bodies unrelated to duplicate identity conflicts.
- Treating product-local SKUs as distinct; SKU uniqueness is global.
- Resetting a test database or repairing production collisions automatically.
- Reworking checkout reservation algorithms already covered by the checkout-order capability.

## Decisions

### Canonicalize in the application and enforce the invariant in PostgreSQL

Use shared application helpers for `trim + lowercase` email normalization and `trim + blank-to-NULL` SKU normalization. Apply them through request validation and defensively in services so non-HTTP callers follow the same rule. PostgreSQL will enforce canonical email storage with a check constraint and normalized uniqueness, and canonical SKU storage with a check constraint plus a partial unique expression index on the case-folded trimmed value for non-`NULL` SKUs.

This keeps stored values predictable while the expression-based unique definitions document the actual identity rule. A PostgreSQL case-insensitive text extension was considered, but it adds extension lifecycle concerns and does not by itself define whitespace handling. Application-only validation was rejected because it cannot close concurrent-write races or protect alternate write paths.

### Preflight existing data without automatic cleanup

The Alembic upgrade will run explicit aggregate checks for normalized email collisions and normalized non-empty SKU collisions before creating any new constraint or index. It will also detect rows that cannot satisfy canonical storage constraints and stop with a concise remediation category and safe diagnostic identifiers/counts, not secrets or full record dumps. The migration will not merge, rename, delete, or silently normalize records; operators must resolve invalid data through an approved process and rerun the migration.

Creating constraints and hoping PostgreSQL's generic failure is sufficient was rejected because it obscures the conflicting rule and can leave less actionable deployment output. Automatic rewriting was rejected because identity changes can affect external references and violates the cleanup policy.

### Translate named database conflicts after rolling back the failed unit of work

Keep friendly preflight lookups where useful, but treat named PostgreSQL uniqueness violations as authoritative. Auth registration and variant create/update will catch only recognized email/SKU integrity targets, roll back the failed transaction boundary as required by the current service pattern, and raise stable HTTP 409 API errors (`email_exists` for email and one documented duplicate-SKU code for both variant operations). Unknown integrity errors continue to propagate.

Preflight-only handling was rejected because two transactions can both pass it. Converting every integrity failure to a duplicate response was rejected because it would conceal unrelated defects.

### Use a conditional atomic UPDATE for quantity deltas

Replace the read-modify-write path for managed quantity adjustments with one database update whose assignment adds the requested delta and whose predicate requires the resulting quantity to remain non-negative. Check the affected-row result, then distinguish a missing listing from insufficient inventory for the existing 404/409 contracts and reload the updated row.

Row locking was considered and would be correct, but a conditional arithmetic update is smaller, naturally prevents lost updates, and locks only the row being changed. Optimistic version columns were rejected as unnecessary for this focused delta operation.

### Build a guarded PostgreSQL test harness with barrier-controlled transactions

Centralize validation of `TEST_POSTGRES_DATABASE_URL`: absence produces an explicit skip; a configured URL must resolve to PostgreSQL before an engine or migration connection is opened. Tests will create uniquely tagged fixtures, open separate sessions/connections per worker, coordinate workers with bounded synchronization barriers, collect both outcomes, and query committed state from a fresh session. Teardown deletes only IDs created by that fixture in foreign-key-safe order.

Concurrency tests will cover equivalent email registration, equivalent SKU create submissions, and both sufficient and oversubscribed inventory reductions. Migration coverage will use isolated test-owned rows to exercise upgrade, downgrade, and re-upgrade, plus collision preflight failures, without dropping schemas or resetting the database. Sleep-based races were rejected as nondeterministic; whole-database teardown was rejected as unsafe.

## Risks / Trade-offs

- [Canonical check constraints expose previously tolerated direct writes] → Document the canonical rules, keep application helpers shared, and fail migration preflight before constraint installation when existing rows violate them.
- [Constraint-name/error matching can vary by driver] → Give migration objects stable names and test real PostgreSQL exceptions while preserving unknown-error propagation.
- [Rolling back inside a service can discard other pending caller work] → Keep write transactions narrow at API boundaries and follow the repository's existing integrity-conflict pattern; tests will verify state preservation for the target record.
- [Barrier tests can hang after a worker failure] → Use bounded barrier waits and future timeouts, always roll back/close worker sessions, and surface the first worker error.
- [Migration lifecycle tests can interfere with other PostgreSQL tests] → Run migration tests in an isolated invocation/serialized group and tag all test-owned data; never run destructive reset operations.

## Migration Plan

1. Add application normalization, conflict translation, and atomic inventory adjustment with SQLite-compatible tests before enabling the new database objects.
2. Add an Alembic revision whose first phase checks normalized collisions and noncanonical values and aborts before schema mutation with actionable errors.
3. On clean data, add stable named email canonical/uniqueness enforcement and SKU canonical/partial-expression uniqueness enforcement, then align SQLAlchemy metadata.
4. Run upgrade, downgrade, and re-upgrade against the explicitly configured PostgreSQL test database and execute barrier-coordinated concurrency tests.
5. Deploy the migration before relying on the new conflict handling in concurrent production traffic.

Downgrade removes only the new indexes and check constraints. It does not rewrite or remove users, variants, listings, or other business data; application normalization may remain compatible during a rolling rollback.
