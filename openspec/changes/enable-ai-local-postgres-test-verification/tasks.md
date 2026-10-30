## 1. Apply Test Environment Contract

- [x] 1.1 Add a narrow runtime helper that reads only `TEST_POSTGRES_DATABASE_URL`, accepts absent configuration, validates PostgreSQL and driver-qualified PostgreSQL URL forms, and returns errors without the raw value; verify focused unit tests cover valid, absent, empty, malformed, and non-PostgreSQL inputs.
- [x] 1.2 Integrate the validated runtime value into apply preflight as in-memory invocation state without adding it to run-record fields; verify apply preflight and serialization tests prove invalid values stop before Codex and valid credentials are never persisted.

## 2. Phase-Scoped Propagation and Redaction

- [x] 2.1 Thread the validated test environment explicitly from apply orchestration into implementation Codex while leaving plan Codex, dry-run execution, status sync, and GitHub subprocess environments unchanged; verify runner and Codex adapter tests assert the variable is present only for approved implementation.
- [x] 2.2 Pass the same validated value to trusted implementation verification so backend `python -m pytest` receives it; verify validation tests capture the child environment and prove PostgreSQL-only tests no longer skip for missing configuration when the variable is supplied.
- [x] 2.3 Redact the exact configured URL from streamed implementation stderr, captured command failures, terminal errors, and recorded errors; verify sentinel URL and password values never appear in output or run-record fixtures.

## 3. Operator Documentation and Full Verification

- [x] 3.1 Update `docs/ai-local-openspec.md` with configuration examples, including setting `TEST_POSTGRES_DATABASE_URL` to the disposable local `stockx` database, and document migration downgrade/re-upgrade, interruption recovery, concurrency, and shared-data risks; verify documented commands match supported behavior.
- [x] 3.2 Run JavaScript syntax checks for changed runner modules, `npm run ai:local:test`, root `npm test`, and `openspec validate enable-ai-local-postgres-test-verification --strict`; record any unrelated failure without weakening the environment-isolation or leak tests.
