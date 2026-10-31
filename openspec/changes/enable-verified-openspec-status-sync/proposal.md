## Why

`--sync-status` currently works only when a successful `ai:local --apply` already wrote a pending Project transition. The intended operator flow instead uses `ai:local` for GitHub-backed planning, `$openspec-apply-change` for implementation, and `--sync-status` for final verification and automatic Project completion; today the final command rejects that flow and forces a manual Project edit.

## What Changes

- Extend `npm run ai:local -- --sync-status <change-name>` with a verified-completion path when no pending transition exists.
- Support the exact three-stage workflow: create the GitHub-backed plan with `--project-owner`, `--project-number`, and `--issue`; implement it with `$openspec-apply-change <change-name>`; then invoke `--sync-status <change-name>` to verify the resulting code and set the selected Project item to `Done`.
- Make a successful `ai:local --apply <change-name>` optional for status synchronization; the successful GitHub-backed plan record remains required, but a pending apply-created transition does not.
- Require a unique successful GitHub-backed plan record, unchanged approved-plan identity apart from task checkmarks, strict OpenSpec validity, every task complete, a reviewable unstaged implementation delta, and all trusted path-selected verification commands to pass before creating a `Done` transition.
- Preserve the existing pending-transition retry as the first and idempotent behavior; an existing pending `Done` or `Blocked` update is retried without rerunning verification.
- Persist a new auditable run record for verified completion, write the pending `Done` intent before GitHub mutation, and retain it if the remote update fails so the same command becomes a normal retry.
- Refuse ambiguous plans, stale or changed contracts, staged changes, unsupported paths, empty implementation deltas, incomplete tasks, failed validation, non-GitHub sources, and Project identity/status drift without mutating GitHub.
- Keep Codex, issue edits, commits, pushes, pull requests, merges, and publication out of status synchronization.

## Capabilities

### New Capabilities

- `verified-openspec-status-sync`: Safe automatic synchronization of a completed, locally verified GitHub-backed OpenSpec change to the configured Project `Done` status.

### Modified Capabilities

None.

## Impact

- Affects the local runner preflight, run-record lookup and schema, validation orchestration, status-sync workflow, terminal output, tests, and `docs/ai-local-openspec.md`.
- Uses existing GitHub CLI authentication and existing trusted verification policies; no new dependency or credential flow is introduced.
- Broadens `--sync-status` from retry-only recovery to retry-or-verify behavior while retaining the same CLI syntax.
- Keeps `ai:local --apply` available as an alternative implementation path without requiring it in the project-local `$openspec-apply-change` workflow.
