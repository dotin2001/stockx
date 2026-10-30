## Why

`ai:local` currently removes `TEST_POSTGRES_DATABASE_URL` from both the implementation Codex process and trusted changed-area verification. PostgreSQL-only tests therefore skip or implementation reports a missing database even when the operator explicitly configured a reachable disposable test database.

## What Changes

- Recognize an operator-provided `TEST_POSTGRES_DATABASE_URL` as an apply-only test dependency.
- Validate that the configured URL uses PostgreSQL before implementation begins.
- Make the URL available to the implementation stage and trusted apply verification, while keeping it out of planning and status-sync processes.
- Treat the URL as sensitive: never print it, persist it in run records, or include it in error output.
- Document that the selected database must be disposable and may be migrated down and back up by the test suite.
- Add runner coverage proving phase isolation, redaction, validation, and PostgreSQL test execution behavior.

## Capabilities

### New Capabilities

- `trusted-local-postgres-test-verification`: Defines explicit, secret-safe PostgreSQL test database injection for approved local implementation and verification.

### Modified Capabilities

None.

## Impact

- Affects `automation/ai-local/lib/codex.mjs`, `automation/ai-local/lib/preflight.mjs`, `automation/ai-local/lib/validation.mjs`, and narrowly scoped environment helpers.
- Adds focused tests under `tests/ai-local/` and updates `docs/ai-local-openspec.md`.
- Does not change application runtime database configuration, GitHub credentials, publication behavior, or plan-stage authority.
