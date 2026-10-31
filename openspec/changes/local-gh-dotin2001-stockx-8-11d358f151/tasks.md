## 1. Retention Service

- [x] 1.1 Add a refresh-token retention service that captures or accepts one UTC cutoff, selects only tokens expired or revoked at least 30 days earlier in deterministic order, and verify focused tests cover both eligibility paths plus exact and just-inside boundary behavior.
- [x] 1.2 Limit selection to one positive batch, implement non-mutating preview and transactional deletion results, and verify service tests cover over-limit populations, accurate counts, repeated-run idempotency, and zero-result runs.
- [x] 1.3 Preserve replacement tokens and rely on the existing `ON DELETE SET NULL` relationship behavior without traversing chains, then verify tests cover eligible predecessors, protected replacements, incoming references, and wholly protected chains.

## 2. Operator CLI

- [x] 2.1 Add a dedicated backend command module and console-script entry point with explicit dry-run mode, a positive `--batch-size`, safe exit codes, and count/cutoff reporting that excludes token hashes; verify CLI tests cover parsing, invalid bounds, preview, deletion, zero results, and sanitized failures.
- [x] 2.2 Apply short PostgreSQL transactions and row-locking/skip-locked behavior to deletion selection, and verify concurrent or lock-contention coverage demonstrates that one invocation never exceeds its batch and reports only actual deletions.

## 3. PostgreSQL Retention Verification

- [x] 3.1 Add an environment-gated PostgreSQL retention test module using the existing explicit test-database safeguards, and verify it passes against the repository PostgreSQL service.
- [x] 3.2 Cover inclusive 30-day expiration and revocation boundaries, protected active/recent tokens, actual deletion, dry-run immutability, bounded deterministic batches, repeated execution, and replacement foreign-key effects in PostgreSQL tests.
- [x] 3.3 Seed representative protected business/payment/webhook rows in PostgreSQL retention tests and verify cleanup leaves `stripe_webhook_events`, orders, payment attempts, listings, users, products, variants, and non-eligible refresh tokens unchanged, with no webhook retry or event-ID reuse behavior added.

## 4. Operator Documentation and Final Checks

- [x] 4.1 Document a recommended daily dry-run followed by one bounded deletion invocation, the one-batch semantics, first-run safeguards, and operator ownership of scheduling; verify the documented commands match the installed console entry point and no scheduler or workflow file is added.
- [x] 4.2 Document separate commands for the normal backend suite and PostgreSQL-specific retention tests, including `TEST_POSTGRES_DATABASE_URL` setup, and verify both command forms collect the intended tests.
- [x] 4.3 Run the normal backend suite and the PostgreSQL-specific retention tests, confirm all acceptance scenarios pass, and verify the final diff contains no database migration, `.github/workflows/` change, scheduler, webhook retry subsystem, or cleanup target beyond explicitly eligible refresh tokens.
