## Why

The local AI runner currently accepts only a repository Markdown task, so it cannot use the team's GitHub Project `Todo` column as its local work inbox. A developer needs a local-only flow that reads the Project, lets them explicitly choose one issue, and then applies the existing plan-before-implementation OpenSpec pipeline without restoring GitHub Actions or publication authority.

## What Changes

- Add a local GitHub Project inbox command that reads all issue items whose configured status is exactly `Todo` and presents them for explicit selection.
- Snapshot the selected issue's identity, title, body, and URL as untrusted task context, then invoke the existing isolated OpenSpec planning, strict validation, implementation, verification, and unstaged patch application flow.
- Support repository-appropriate Project owner/number configuration plus a deterministic non-interactive issue selector for repeatable testing, while keeping interactive selection as the normal operator experience.
- Add fail-closed preflight checks for the GitHub CLI, authentication, required Project read scope, malformed or unsupported Project items, empty `Todo` results, and stale issue selections.
- Preserve local-only authority: the flow does not change Project status, edit issues, comment, commit, branch, push, open pull requests, merge, or run in GitHub Actions, and GitHub credentials are never exposed to Codex.
- Document setup, selection, execution, result review, and recovery for the GitHub Project-backed local flow.

## Capabilities

### New Capabilities

- `local-github-project-inbox`: Read a configured GitHub Project's `Todo` issue items locally, require an explicit issue choice, and hand a validated immutable snapshot to the local AI OpenSpec runner.

### Modified Capabilities

- None.

## Impact

- Affected areas: root package commands, `bin/`, `automation/ai-local/`, `tests/ai-local/`, local-runner documentation, and repository agent/project guidance.
- Adds the GitHub CLI as a prerequisite only for Project-backed intake; the existing Markdown `--task` mode remains available without GitHub.
- Uses the operator's local GitHub CLI authentication for read-only Project and issue retrieval. No GitHub token is passed to Codex or written to task context/run records.
- Does not restore `.github/workflows`, GitHub-hosted AI execution, Project mutations, or pull-request publication.
