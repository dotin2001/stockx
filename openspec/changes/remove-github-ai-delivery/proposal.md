## Why

The repository currently contains two AI delivery paths, while the desired operating model is a single local OpenSpec runner. Removing the unfinished GitHub Actions path reduces credentials, workflow authority, documentation, and maintenance surface without changing marketplace behavior.

## What Changes

- **BREAKING** Remove the GitHub Actions AI delivery and pull-request observer workflows, their trusted prompts, schemas, and orchestration helpers.
- **BREAKING** Remove the `ai:workflow:test` package command and the GitHub-delivery test suite.
- Remove the GitHub Project AI delivery operator guide and its repository guidance.
- Remove the unarchived `automate-github-project-ai-openspec-flow` change because that feature will no longer exist.
- Keep `ai:local`, its implementation, tests, OpenSpec artifacts, and operator guide as the repository's only AI OpenSpec delivery path.
- Update local-runner documentation and repository guidance so they describe a local-only model rather than two independent delivery modes.

## Capabilities

### New Capabilities

- None. This change removes repository automation and documentation rather than adding behavior.

### Modified Capabilities

- None. The GitHub delivery capability exists only in the unarchived change being removed and was never promoted to the main specifications. This tooling-only removal therefore opts out of delta specs.

## Impact

- Deletes `.github/workflows/ai-openspec-*.yml`, `.github/codex/`, `tests/ai-workflow/`, `docs/ai-openspec-delivery.md`, and `openspec/changes/automate-github-project-ai-openspec-flow/`.
- Updates `package.json`, `AGENTS.md`, `project.md`, local-runner documentation, and local-runner source-contract tests.
- Removes all repository-managed GitHub Project polling, status mutation, issue comments, AI pull-request publication, and merge observation.
- Retains the local CLI, local Codex authentication, temporary-worktree isolation, validation, and unstaged human-review workflow.
