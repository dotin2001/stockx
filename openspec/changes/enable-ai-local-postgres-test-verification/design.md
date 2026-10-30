## Context

See `proposal.md` for motivation and `specs/trusted-local-postgres-test-verification/spec.md` for the required behavior. The runner currently builds a small allowlisted environment in `process.mjs`; `runCodexStage` uses it for both plan and implementation, and `validationEnvironment` independently rebuilds it for trusted checks. This correctly excludes arbitrary host credentials, but it also removes the explicitly configured PostgreSQL test URL from apply.

The value can contain a password. It must not be passed during untrusted issue planning, interpolated into commands or prompts, printed in output, or serialized into `.ai-local/runs/`. Apply is the appropriate boundary because its input is the reviewed OpenSpec contract rather than raw issue text.

## Goals / Non-Goals

**Goals:**

- Validate one named PostgreSQL test variable at apply preflight.
- Share it only with implementation Codex and host-side implementation verification.
- Preserve existing default behavior when the variable is absent.
- Redact the exact URL from streamed and captured errors.
- Prove phase isolation and non-persistence with automated tests.

**Non-Goals:**

- Provisioning PostgreSQL, creating databases, or checking whether a database is disposable.
- Passing the application `DATABASE_URL` implicitly or discovering credentials from files.
- Allowing arbitrary environment variables through to Codex.
- Guaranteeing successful tests, model availability, or absence of legitimate task blockers.
- Preventing an explicitly approved implementation process from connecting to the supplied test database.

## Decisions

### Add an apply-specific test environment instead of expanding the global allowlist

Create a narrow helper that reads only `TEST_POSTGRES_DATABASE_URL`, validates its URL scheme, and returns an immutable apply test-environment object. Apply preflight obtains this object and keeps it in memory for the current invocation. Planning continues to use the existing sanitized environment unchanged.

This is preferred over adding the variable to `PASSTHROUGH_ENV`, which would unnecessarily expose it to plan Codex, OpenSpec planning checks, GitHub commands, and every other child process.

### Validate syntax and dialect without connecting during preflight

Accept the SQLAlchemy PostgreSQL forms used by this project, including `postgresql://` and driver-qualified forms such as `postgresql+psycopg://`. Reject empty, malformed, and other-dialect values before implementation. Connectivity remains the responsibility of the actual tests so preflight does not mutate or probe database state.

This is preferred over opening a database connection in preflight because a connection is not needed to establish phase authority and could create side effects before explicit implementation begins.

### Pass runtime data explicitly through apply orchestration

Extend the implementation-stage call and implementation validator to accept the in-memory test environment explicitly. `runCodexStage` adds it only when `phase === "implementation"`; `validationEnvironment` adds it only for trusted implementation checks. Dry-run returns after validation and before either consumer is invoked.

Explicit arguments are preferred over rereading `process.env` in multiple modules because they make authority visible, avoid accidental use from planning, and are straightforward to test with injected dependencies.

### Redact at every output boundary and never persist the value

Keep the URL out of prompts, task context, result objects, and run-record fields. Add the value to the secret set used for child-process failure sanitization and sanitize streamed implementation stderr before forwarding it to terminal output. Tests will use sentinel credentials and assert their absence from output and serialized records.

This complements, rather than replaces, the implementation prompt's instruction not to inspect credentials. The security property must be enforced by the host runner even if a child command echoes its environment.

### Treat database selection as explicit operator responsibility

The runner validates only that the URL is PostgreSQL. It does not reject the database name `stockx` or require a `_test` suffix because names do not prove safety. Documentation states that using the same URL as `DATABASE_URL` is supported only for a disposable local database and describes migration downgrade/re-upgrade risk.

## Risks / Trade-offs

- [Implementation Codex receives a database credential] → Limit exposure to reviewed apply, pass only the one named variable, keep GitHub credentials excluded, and document that it must target a disposable test database.
- [A child process could echo the URL] → Redact the exact runtime value from streamed stderr, captured command failures, and persisted errors; add sentinel leak tests.
- [A valid PostgreSQL URL can still target valuable data] → Require an explicit operator variable and prominent lifecycle warning; do not claim database-name heuristics provide safety.
- [Tests can leave the database downgraded after interruption] → Document recovery with `alembic upgrade head` and keep migration lifecycle checks responsible for restoring `head` during normal completion.
- [Absent configuration still permits skipped PostgreSQL tests] → Preserve compatibility rather than making every apply require PostgreSQL; individual approved plans may require the variable and report a clear blocker when it is absent.

## Migration Plan

1. Add URL parsing/validation and an apply-only runtime environment contract with leak-focused unit tests.
2. Thread that contract through apply preflight, implementation Codex, and trusted implementation validation without changing planning or status-sync environments.
3. Add orchestration and source-contract tests for valid, invalid, absent, dry-run, failure-redaction, and run-record cases.
4. Update operator documentation with configuration and database lifecycle warnings.
5. Run syntax checks, `npm run ai:local:test`, root `npm test`, and strict OpenSpec validation.

Rollback removes the apply-specific environment wiring and documentation. Existing run records require no migration because they never store the URL.
