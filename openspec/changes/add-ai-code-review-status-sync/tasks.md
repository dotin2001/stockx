## 1. Provenance and Project Status Model

- [x] 1.1 Add `--review-status` with default `Review`, persist distinct source/Done/Review/Blocked names and additive review metadata in task/source and run records, and verify CLI/task/run-record tests cover explicit, default, invalid, and legacy version-3 records.
- [x] 1.2 Add host-side refresh of the exact recorded Project item and issue, reconstruct its canonical task identity, and verify repository/number/item/url/task hash before review; verify GitHub adapter and preflight tests stop without mutation for missing, changed, ambiguous, or inaccessible issue evidence.
- [x] 1.3 Verify the attached branch equals the recorded branch and the recorded base is a valid ancestor commit of current `HEAD`; verify focused tests cover matching history, later commits, detached checkout, renamed branch, missing base, and rebased/non-ancestor history.
- [x] 1.4 Extend Project option resolution and mutation for Done, Review, and conditional Blocked, including Blocked-to-Review fallback and safe source/Review/review-produced-Blocked transitions; verify adapter tests reject unrelated current states and record fallback provenance without editing the issue.
- [x] 1.5 Extend evidence resolution so one pending Done/Review/Blocked intent has exact retry priority, synchronized Done is terminal, and synchronized Review or review-produced Blocked enters fresh review; verify ambiguity, idempotency, recovery, and legacy-evidence tests.

## 2. Complete Read-Only Change and Check Evidence

- [x] 2.1 Replace working-tree-only completion inspection with a read-only recorded-base-to-working-tree collector covering committed, staged, unstaged, deleted, and untracked paths without `git add -N`; verify unit fixtures include every state, safe-path rejection, binary/large files, and unchanged index bytes.
- [x] 2.2 Capture a bounded review snapshot containing branch, base, `HEAD`, status/index/untracked identities, path union, tracked and untracked digests, approved-plan hash, and issue task hash; verify revalidation tests reject concurrent commits, checkouts, staging, edits, untracked changes, plan drift, and issue drift.
- [x] 2.3 Select trusted checks from the complete base-to-current path union and collect PASS, FAIL, or BLOCKED results instead of aborting for ordinary test outcomes; verify `git diff --check` includes committed changes and frontend, backend/PostgreSQL, runner, strict-OpenSpec, missing-tool, missing-environment, and failing-command cases are classified correctly.
- [x] 2.4 Detect any Git-visible mutation caused during checks or review and stop before status preparation; verify tests simulate source, index, branch, and commit mutations while allowing ignored test/build caches.

## 3. Structured Read-Only Codex Review

- [x] 3.1 Add a bounded review schema for issue/OpenSpec/task/check inventory entries with source, identifier, PASS/FAIL/BLOCKED result, evidence, remaining work, summary, and human-review reasons; verify contract tests reject missing coverage, duplicate ids, inconsistent PASS/remaining-work pairs, oversized fields, and malformed results.
- [x] 3.2 Add a repository-controlled prompt that enumerates linked-issue acceptance criteria, evaluates the full base-to-current implementation against issue and OpenSpec requirements, treats all inputs as untrusted data, cites evidence, and requests human review for ambiguity; verify source-contract tests lock these instructions and prohibit status selection or implementation edits.
- [x] 3.3 Create restrictive ephemeral issue/check context for the reviewer without persisting raw bodies or logs, and remove it after review; verify lifecycle and redaction tests prove raw issue content, command output, credentials, and environment values do not enter run records or terminal output.
- [x] 3.4 Extend Codex invocation with a `review` phase using the pinned model, read-only sandbox, ignored user configuration, sanitized environment, empty GitHub configuration, and private structured-result capture; verify adapter tests prove no GitHub credential, apply-only database value, or write-capable sandbox reaches review.
- [x] 3.5 Validate deterministic coverage and report consistency, and synthesize a bounded BLOCKED semantic-review entry when Codex cannot run or return a valid complete report; verify failure, timeout, authentication, invalid-schema, omitted-entry, and prompt-injection tests.

## 4. Review Orchestration, Reporting, and Status Routing

- [x] 4.1 Orchestrate fresh sync in the required order—run-record provenance, issue/branch/base verification, complete diff snapshot, issue/OpenSpec evaluation, trusted checks, structured report, stable-snapshot recheck, then Project preparation—and verify call-order tests prove provenance failures perform no Codex, check, pending-intent, or mutation action.
- [x] 4.2 Derive Done only for all-PASS/no-human-review reports, Review for any FAIL/check failure/human review/mixed FAIL-BLOCKED report, and Blocked for failure-free unavailable verification; verify table-driven tests cover every aggregate combination without accepting a model-provided target.
- [x] 4.3 Implement conditional Blocked-to-Review fallback with explicit derived/effective targets and blocker explanation, then persist the effective pending intent before mutation; verify missing/duplicate Blocked and Review option tests plus remote-failure recovery retain exactly one auditable retry.
- [x] 4.4 Keep synchronized Review and review-produced Blocked eligible for fresh base-to-current review while keeping synchronized Done idempotent; verify corrected commits and restored verification prerequisites can progress to Done.
- [x] 4.5 Print and persist bounded sanitized per-requirement results, evidence, remaining work, human-review reasons, derived/effective status, fallback explanation, verification names, and run-record path; verify output and record tests cover PASS, FAIL, BLOCKED, fallback, and secret redaction without raw issue/model/check content.

## 5. Integration and Operator Contract

- [x] 5.1 Add an offline integration fixture with a verified issue and branch plus committed, staged, unstaged, deleted, and untracked changes since base; verify one review report covers the full path set and can reach Done without modifying implementation or index state.
- [x] 5.2 Add integration fixtures for missing/changed issue identity, detached/wrong branch, missing/non-ancestor base, and concurrent checkout mutation; verify every case stops with a local error and leaves Project status unchanged.
- [x] 5.3 Add end-to-end result fixtures for failed requirements/checks to Review, unavailable verification to Blocked, unavailable Blocked option to Review fallback, corrected Review to Done, unblocked Blocked to Done, and failed remote update to model-free exact retry.
- [x] 5.4 Verify security integration contracts: issue/code prompt injection cannot change policy, Codex receives no GitHub credentials, review makes no Git-visible edit, and the host never comments on, edits, labels, assigns, or closes the issue and never commits, pushes, merges, or publishes.
- [x] 5.5 Update CLI help, `AGENTS.md`, and `docs/ai-local-openspec.md` with the seven-step workflow, base/history rules, full diff scope, PASS/FAIL/BLOCKED meanings, status precedence and fallback, local report format, re-review, exact retry, and read-only guarantees; verify source-contract tests cover the operator guidance.
- [x] 5.6 Run `npm run ai:local:test`, the full `npm test` suite, and `openspec validate add-ai-code-review-status-sync --strict`, and mark completion only after all checks pass.
