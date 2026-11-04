## 1. Host Check Status Policy

- [x] 1.1 Add a deterministic host-check status derivation helper with `FAIL` → Review, otherwise `BLOCKED` → Blocked, otherwise non-empty all-`PASS` → Done; verify focused unit tests cover all-pass, fail, blocked, mixed, and empty inputs
- [x] 1.2 Refactor fresh status-sync orchestration to derive its target from collected host checks and skip Codex semantic review as a status prerequisite; verify an all-pass runner test reaches Done without invoking the review stage
- [x] 1.3 Preserve post-check snapshot and linked-issue identity revalidation before Project preparation; verify stale snapshot and stale issue tests still prevent every remote mutation

## 2. Records, Recovery, and Output

- [x] 2.1 Record `trusted-host-verification` as the completion basis together with authoritative check results and derived/effective targets, without fabricating semantic requirement PASS entries; verify run-record assertions cover Done, Review, and Blocked outcomes
- [x] 2.2 Preserve exact pending-transition retry and nonterminal Review/Blocked re-verification; verify retry tests do not rerun checks and corrected or unblocked checks can advance to Done
- [x] 2.3 Update terminal formatting to explain host-authoritative completion and list failed or blocked checks without requiring a semantic report; verify bounded sanitized output tests cover all three targets

## 3. Documentation and Regression Verification

- [x] 3.1 Update `AGENTS.md` and `docs/ai-local-openspec.md` to document that path-selected trusted checks are authoritative, all-pass yields Done, and semantic acceptance review no longer gates status; verify documented commands and status precedence match implementation
- [x] 3.2 Run the complete local-runner test suite and strict OpenSpec validation; verify all tests pass and `openspec validate trust-host-checks-for-status-sync --strict` succeeds
