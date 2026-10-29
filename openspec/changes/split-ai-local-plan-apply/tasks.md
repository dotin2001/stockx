## 1. Lifecycle Contracts

- [x] 1.1 Extend CLI parsing with mutually exclusive plan intake, `--apply <change-name>`, and `--sync-status <change-name>` modes plus frozen `Done`/`Blocked` Project option names; verify focused argument tests cover valid forms, conflicts, empty names, and dry-run behavior.
- [x] 1.2 Version the local run-record contract for plan, apply, and status-sync lifecycles, including parent plan identity, approved-plan digest, Project status configuration, and pending/synchronized transitions; verify serialization tests exclude issue bodies and credentials.
- [x] 1.3 Add safe successful-plan record discovery by exact change name and source identity; verify malformed, failed, ambiguous, and missing records are rejected before Codex or GitHub mutation.

## 2. Plan-Only Intake

- [x] 2.1 Split the current orchestration so Markdown and Project intake execute planning, strict plan validation, and plan-patch application only; verify orchestration tests prove implementation is never invoked during intake.
- [x] 2.2 Record the validated plan paths and digest and emit review guidance with the exact `--apply` command; verify success output states that implementation and Project mutation did not run.
- [x] 2.3 Preserve failure containment for clarification, invalid plans, checkout drift, and interruption; verify each path leaves the original checkout and GitHub item unchanged.

## 3. Approved Apply Transaction

- [x] 3.1 Add apply preflight that validates the change name, loads its successful plan record, accepts either a committed plan or unstaged changes limited to the exact change directory, and rejects staged or unrelated changes; verify repository-state tests cover every allowed and rejected shape.
- [x] 3.2 Implement deterministic approved-plan discovery and hashing across schema metadata, proposal, optional design, capability specs, and task text normalized only for checkbox state; verify edits to requirements or task wording change the digest while checkbox updates do not.
- [x] 3.3 Recreate an approved uncommitted plan in the isolated worktree and establish it as the temporary index baseline without creating a commit; verify captured implementation patches exclude plan additions but include task-checkbox and project-file changes.
- [x] 3.4 Add apply orchestration that runs only the implementation prompt, validates against the approved plan, executes trusted checks, rechecks checkout/plan identity, and applies the implementation delta unstaged; verify success and stale-state integration tests.
- [x] 3.5 Enforce approved-contract immutability and truthful task completion during implementation; verify proposal, design, spec, schema, or task-text rewrites fail while checkbox-only completion succeeds.

## 4. Blocked Outcomes and Project Status

- [x] 4.1 Extend the implementation prompt, JSON schema, and result parser with a constrained structured `blocked` outcome and required actionable summary; verify technical failures remain distinguishable from task blockers.
- [x] 4.2 Add GitHub Project field/option resolution and exact-item status mutation through the host `gh` session; verify fake-transport tests cover missing or ambiguous fields/options, identity drift, allowed transitions, and credential isolation.
- [x] 4.3 Map a validated local apply to `Done`, a structured task blocker to `Blocked`, and every other apply failure to no Project mutation; verify orchestration tests assert both positive mutations and all no-mutation failure cases.
- [x] 4.4 Persist pending status transitions before remote mutation and add no-model `--sync-status` recovery; verify a failed update retains local implementation and retry can perform only the recorded exact transition.

## 5. Operator Experience and Verification

- [x] 5.1 Update terminal output and exit handling for plan-ready, apply-success, blocked, and status-sync-failed outcomes; verify CLI integration tests include actionable review, apply, and retry commands.
- [x] 5.2 Replace read-only/one-shot assertions in source-contract tests with narrow host-mutation allowlisting while continuing to forbid GitHub credentials in Codex, issue edits, publication, commits, pushes, pull requests, and arbitrary Project operations; verify the focused contract suite passes.
- [x] 5.3 Update `docs/ai-local-openspec.md` and `AGENTS.md` with the two-stage commands, approval semantics, status classification, recovery flow, and local-record portability constraint; verify documented commands match CLI help.
- [x] 5.4 Run JavaScript syntax checks, `npm run ai:local:test`, the root `npm test`, and `openspec validate split-ai-local-plan-apply --strict`; record any unrelated repository failures without weakening the new workflow checks.
