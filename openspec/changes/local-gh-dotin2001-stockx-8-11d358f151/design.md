## Context

See `proposal.md` for motivation and `specs/backend-retention-cleanup/spec.md` for the behavior contract. Refresh tokens already carry timezone-aware `expires_at`, nullable `revoked_at`, and a self-referencing `replaced_by_token_id` whose foreign key uses `ON DELETE SET NULL`. The backend already exposes operator commands through Python entry points, uses SQLAlchemy sessions, and has PostgreSQL test helpers gated by `TEST_POSTGRES_DATABASE_URL`. There is no general retention framework or scheduler.

## Goals / Non-Goals

**Goals:**

- Keep eligibility, deterministic selection, dry-run, deletion, and reporting in a small service that can be tested independently of argument parsing.
- Make every invocation transactionally safe, capped to one operator-selected batch, and repeatable.
- Exercise database-specific timestamp and self-reference behavior on PostgreSQL.

**Non-Goals:**

- A generic table-cleanup framework, schema migration, background worker, deployment scheduler, or hosted CI configuration.
- Stripe webhook deletion or retries, including any interpretation of failed processing as exhausted retries.
- Retention for business, payment, catalog, user, inventory, or audit records.

## Decisions

### Use one fixed cutoff per invocation

The command will capture a timezone-aware current time once and derive `cutoff = now - 30 days`. Eligibility is the inclusive predicate `expires_at <= cutoff OR revoked_at <= cutoff`. Passing the cutoff into the service for tests avoids boundary drift between queries. A configurable retention interval was rejected because the policy is fixed and allowing shorter operator-selected windows would weaken the safety guarantee.

### Process exactly one bounded batch per invocation

The CLI will accept a positive `--batch-size` with a conservative default and select at most that many eligible IDs in deterministic timestamp-and-ID order. It will not loop until the table is drained. This bounds transaction duration and lock pressure; daily automation can invoke it repeatedly over time. An unbounded delete or an internal drain loop was rejected because either can create unexpectedly large transactions.

### Share selection logic between dry-run and deletion

A retention service will build one eligible-ID selection with the fixed cutoff, deterministic ordering, and limit. Dry-run returns the selected count then rolls back or performs no write; deletion removes precisely those selected rows and commits once. The CLI reports mode, cutoff, batch size, and selected/deleted count without exposing token hashes. Duplicated preview and delete predicates were rejected because they can drift.

### Rely on the existing replacement foreign key

Deleting an eligible predecessor is safe because its outgoing link does not own the replacement, while incoming links to a deleted token are nulled by `ON DELETE SET NULL`. The service will not cascade through a replacement chain and will not make related records eligible. Manual relationship rewriting was rejected because it would duplicate database referential-integrity behavior and could accidentally alter protected rows.

### Use PostgreSQL integration tests plus lightweight CLI tests

PostgreSQL tests will create isolated records in the explicitly configured test database and verify inclusive boundaries, foreign-key effects, dry-run, deletion, batching, idempotency, and protected tables/rows. CLI-focused tests can inject a session factory and clock/service inputs to verify validation, exit codes, and reporting. The existing environment-gated helper keeps these tests local- and CI-ready without adding a workflow.

### Expose a dedicated backend entry point and operator documentation

Add a narrowly named console script following the existing admin, smoke, and reconciliation command pattern. Document a recommended daily preview followed by one deletion batch, plus normal and PostgreSQL-specific pytest commands. Scheduling remains external so deployment-specific concurrency and timing stay operator controlled.

## Risks / Trade-offs

- [Concurrent cleanup invocations may select overlapping rows] → Keep each operation in a short transaction and use PostgreSQL row-locking with skip-locked semantics for deletion selection; report only rows actually deleted.
- [A single batch may not keep up with unusually high token churn] → Make batch size explicit and observable so operators can tune it or invoke more frequently while each transaction stays bounded.
- [Dry-run results can differ from a later deletion as time and data change] → Report the cutoff and describe dry-run as a preview, while ensuring both modes use identical logic for their own invocation.
- [Deleting a referenced token clears an incoming replacement pointer] → Accept the existing `ON DELETE SET NULL` policy and test it explicitly; never delete the referenced replacement unless independently eligible.

## Migration Plan

1. Add the retention service and dedicated CLI entry point without changing the schema.
2. Add unit/CLI coverage and PostgreSQL retention integration tests.
3. Document test commands and the operator-controlled daily dry-run/deletion sequence.
4. Deploy the backend package, run the PostgreSQL-specific tests, then perform a dry run before the first bounded deletion.

Rollback is removal or disabling of the new command; no schema rollback or restoration migration is required. Rows already deleted under the approved policy are not reconstructable, so the initial dry run and bounded first execution are operational safeguards.
