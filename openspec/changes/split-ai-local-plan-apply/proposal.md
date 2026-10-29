## Why

The current local runner validates an OpenSpec plan and immediately starts implementation in the same invocation, so an implementation failure discards the otherwise reviewable plan and gives the operator no approval gate. The runner should persist a validated plan, stop for human review, and resume implementation only through an explicit second command while keeping GitHub Project status aligned with the final task outcome.

## What Changes

- **BREAKING** Change normal Markdown and GitHub Project intake runs from plan-and-implement to plan-only: create and strictly validate the OpenSpec artifacts, apply only those artifacts to the operator checkout, and stop.
- Add an explicit apply mode that accepts one previously planned OpenSpec change, treats invocation as human approval, revalidates the current plan, and runs the existing isolated implementation and verification pipeline.
- Allow apply mode to start from a checkout whose only changes are the selected OpenSpec plan, while continuing to reject unrelated or stale worktree changes.
- Persist enough trusted local metadata to bind an approved change to its original task or selected GitHub Project item without persisting issue bodies or credentials.
- For GitHub-backed changes, let the host runner update only the selected Project item's configured status field after apply: `Done` after validated local patch application, or `Blocked` only for a structured task blocker. Transient model, network, runner, or verification failures remain `Todo`.
- Keep GitHub credentials out of Codex, keep implementation output unstaged and uncommitted, and provide explicit recovery when local implementation succeeds but Project status synchronization fails.
- Update CLI help, run records, validation policy, tests, documentation, and repository guidance for the two-stage lifecycle.

## Capabilities

### New Capabilities

- `human-approved-local-ai-delivery`: Defines persistent plan-only intake, explicit approved apply, safe resume validation, and narrowly scoped GitHub Project terminal-status synchronization.

### Modified Capabilities

None. The earlier local-runner capabilities remain in active change artifacts rather than the synchronized main specification set.

## Impact

- Affects `bin/ai-local.mjs`, `automation/ai-local/lib/`, trusted prompts and result schemas, `tests/ai-local/`, `docs/ai-local-openspec.md`, `AGENTS.md`, and related source-contract checks.
- Changes the default behavior of existing `npm run ai:local -- --task ...` and Project intake commands to stop after planning.
- Adds a local apply invocation and controlled GitHub Project mutation through the operator's existing `gh` session; it does not add GitHub Actions, commits, pushes, pull requests, or credentials to agent processes.
