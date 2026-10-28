## 1. Local CLI Foundation

- [x] 1.1 Add the `bin/ai-local.mjs` entry point, `automation/ai-local` module/prompt/schema layout, `.ai-local/` ignore rule, and root `ai:local` / `ai:local:test` package scripts, and verify every referenced path resolves from the repository root.
- [x] 1.2 Implement typed local-run errors, secret-aware message sanitization, dependency-injected process execution, and phase-oriented output helpers, and verify unit tests cover non-zero exits, signals, missing commands, and credential redaction.
- [x] 1.3 Implement task-file realpath containment, non-symlink regular Markdown validation, first-heading parsing, deterministic bounded `local-<slug>` naming, content hashing, and existing-change collision rejection, and verify malicious, missing, empty, outside-root, and colliding fixtures fail before model use.
- [x] 1.4 Implement Git root, attached-branch, clean/conflict-free status, base-commit, Node, Git, OpenSpec 1.12.x, Codex CLI/flag, authentication-readiness, and temporary-storage preflight checks, and verify each missing or incompatible prerequisite produces a sanitized actionable failure.
- [x] 1.5 Implement atomic ignored run records with version, task path/hash, base, tool versions, phase, timestamps, outcome, changed paths, verification names, and sanitized errors, and verify records never contain task bodies, environment dumps, raw transcripts, or credential values.

## 2. Trusted Agent Contracts

- [x] 2.1 Add the local planning prompt requiring `AGENTS.md`, the repository propose skill, the exact derived change name, inert task context, schema-complete planning, strict validation, and no non-plan edits, and verify prompt contract tests cover every authority boundary.
- [x] 2.2 Add the local implementation prompt requiring the repository apply skill, accepted artifacts as source of truth, truthful task markers, scoped edits, relevant checks, and no Git/GitHub publication, and verify prompt contract tests cover every authority boundary.
- [x] 2.3 Add strict planning and implementation result JSON Schemas plus result parsing that rejects malformed, extra, authority-expanding, or phase-inconsistent fields, and verify valid success/clarification/failure fixtures and invalid fixtures.
- [x] 2.4 Implement shell-free `codex exec` argument construction using ephemeral workspace-write execution, repository-controlled prompts/schemas, final-message files, the temporary worktree root, and supported local authentication without reading or logging secrets, and verify offline tests assert the exact safe arguments and scrubbed child environment.

## 3. Isolated Worktree and Validation

- [x] 3.1 Implement creation and verified cleanup of an owned detached temporary Git worktree at the recorded base, including supported interruption handling and stale-owned-worktree detection, and verify temporary-repository tests preserve the original checkout on success, failure, and interruption.
- [x] 3.2 Implement planning diff capture and validation for safe paths, deterministic change-directory scope, required schema artifacts, clarification handling, and strict OpenSpec validation, and verify out-of-scope, incomplete, malformed, empty, and invalid-plan fixtures cannot start implementation.
- [x] 3.3 Implement combined implementation diff validation for a non-empty implementation, protected authority paths, completed task markers, recorded base/task identity, strict OpenSpec validation, and hard-coded changed-area verification commands, and verify unsafe paths, authority edits, incomplete tasks, stale metadata, unknown areas, and failed checks fail closed.
- [x] 3.4 Implement binary patch creation plus final original-checkout base/cleanliness revalidation, `git apply --check`, unstaged patch application, and no-stage/no-commit guarantees, and verify stale, conflicting, and successful patch fixtures leave the expected original checkout state.

## 4. Orchestration and Operator Experience

- [x] 4.1 Implement CLI argument/help handling for exactly one `--task` and optional `--dry-run`, and verify unsupported, duplicate, missing, and valid argument combinations return documented exit codes and messages.
- [x] 4.2 Orchestrate preflight, isolated planning, plan validation, isolated implementation, combined validation, final patch application, run-record updates, and guaranteed cleanup in order, and verify a fake-Codex integration test proves implementation is gated on validated planning.
- [x] 4.3 Implement dry-run output that reports resolved task, change, base, tools, and planned stages without creating a worktree, invoking Codex, or changing tracked files, and verify the behavior in a temporary repository.
- [x] 4.4 Implement final success/failure output with changed paths, verification summary, run-record path, and explicit human review instructions, and verify output never claims a commit, push, pull request, or GitHub status mutation.

## 5. Offline Security and Integration Tests

- [x] 5.1 Add Node tests for task intake, identity bounds, preflight, redaction, result schemas, run records, and CLI parsing, and verify they pass without network, Codex authentication, GitHub, or OpenAI calls.
- [x] 5.2 Add temporary-Git-repository tests for worktree lifecycle, plan/implementation scope, protected paths, task markers, binary patches, stale bases, conflicts, atomic apply behavior, and cleanup, and verify they cannot alter the developer repository.
- [x] 5.3 Add fake Codex/OpenSpec executable integration tests for success, clarification, planning failure, implementation failure, validation failure, interruption, and original-checkout drift, and verify only the complete success path applies an unstaged diff.
- [x] 5.4 Add source-contract tests confirming the local runner contains no GitHub API/CLI requirement, Project token, branch publication, commit, push, pull-request, scheduled trigger, danger-full-access, or automatic-approval behavior, and verify existing GitHub workflow tests remain unchanged and passing.

## 6. Documentation and Controlled Local Rollout

- [x] 6.1 Document installation prerequisites, supported Codex authentication, task-file format, clean-checkout requirement, dry run, normal run, phase/output interpretation, review/commit/discard steps, failure recovery, stale-worktree cleanup, run-record privacy, and the absence of GitHub mutations, and verify every documented command maps to implemented behavior.
- [x] 6.2 Update `AGENTS.md` and `project.md` with the local runner's plan/apply boundary, protected authority, human-review rule, and distinction from the GitHub Actions flow, and verify repository guidance is coherent with this proposal, design, and specification.
- [x] 6.3 Run the local-runner tests, existing AI workflow tests, relevant root tests, JavaScript syntax checks, and strict validation for `add-local-ai-openspec-runner`, and record any unrelated baseline failures without weakening local-runner success criteria.
- [x] 6.4 Run `ai:local` dry-run in a clean disposable checkout and verify no model invocation, temporary worktree leak, run mutation beyond ignored metadata, or tracked-file change occurs.
- [x] 6.5 Run one low-risk local task in a clean disposable branch with supported Codex authentication, verify separated planning/implementation and validations, inspect the resulting unstaged diff, rerun its reported checks manually, and discard or commit only after human review.
