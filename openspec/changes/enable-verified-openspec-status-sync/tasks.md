## 1. Resolve and Validate Completion Evidence

- [x] 1.1 Extend status-sync evidence lookup to prioritize a unique pending transition, recognize an already synchronized terminal result, and otherwise resolve one unique successful GitHub-backed plan while ignoring non-authoritative failed apply records; verify focused run-record tests cover missing, ambiguous, Markdown, pending, synchronized, failed-apply, and plan-fallback cases.
- [x] 1.2 Add read-only checkout inspection for an attached branch with no staged files, a non-empty unstaged implementation delta, completed task markers, at least one non-plan path, and no protected or unsupported paths; verify tests prove inspection neither stages files nor changes the checkout.
- [x] 1.3 Reuse normalized approved-plan hashing, strict OpenSpec validation, path-selected trusted checks, and apply-only test environment forwarding for completion verification; verify plan drift, incomplete tasks, unknown paths, missing PostgreSQL configuration, and failed checks all stop before GitHub preparation or mutation.

## 2. Orchestrate Verified Status Synchronization

- [x] 2.1 Refactor `--sync-status` orchestration so pending retries remain remote-only while the no-pending path verifies an `$openspec-apply-change` implementation without invoking Codex or applying patches; verify orchestration tests distinguish the two paths and assert no model or checkout mutation calls.
- [x] 2.2 For verified completion, write linked sanitized provenance and changed paths, prepare the recorded Project item, persist a pending `Done` transition before mutation, and mark it synchronized only after success; verify a simulated GitHub failure leaves exactly one retryable pending transition.
- [x] 2.3 Make repeated synchronization idempotent for an already synchronized record and for remote `Done` after an uncertain update; verify it cannot select another item, field, target, or source identity and does not rerun expensive validation.

## 3. Preserve Security and Compatibility

- [x] 3.1 Keep version-3 plan and pending records usable while adding an explicit completion-basis value to new status-sync records; verify serialization contains plan identity, verification names, and state but excludes issue bodies, prompts, raw output, environment dumps, credentials, and the configured test database URL.
- [x] 3.2 Add refusal-path coverage for staged changes, empty or plan-only deltas, protected authority changes, incomplete/changed OpenSpec artifacts, ambiguous records, non-GitHub sources, and Project identity/status drift; verify every refusal records a technical failure and performs zero GitHub mutations.
- [x] 3.3 Update CLI help, terminal output, and `docs/ai-local-openspec.md` with the exact GitHub plan → `$openspec-apply-change` → `--sync-status` commands, retry-or-verify semantics, required local state, failure recovery, and the fact that status sync never closes issues or publishes code; verify source-contract tests cover the new operator guidance.

## 4. End-to-End Verification

- [x] 4.1 Add an offline integration fixture representing GitHub-backed planning followed by `$openspec-apply-change` completion and no successful `ai:local --apply` record; verify `--sync-status` runs trusted checks, records pending-before-mutation, and reaches `Done` without Codex or patch application.
- [x] 4.2 Extend the integration fixture with one or more prior technical `ai:local --apply` failures and verify they neither authorize the transition nor prevent the current completed implementation from reaching `Done` after trusted verification.
- [x] 4.3 Run `npm test`, strict OpenSpec validation for this change, and repository diff checks; verify all tests pass and existing plan, apply, blocked, pending-retry, PostgreSQL verification, and GitHub safety behavior remains unchanged.
