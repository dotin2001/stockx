## Why

The existing AI OpenSpec delivery path depends on GitHub Actions, GitHub Project configuration, and repository secrets, which prevents a developer from running the same plan-before-implementation discipline directly in a local checkout. A local CLI should accept an explicit task file, use the developer's installed Codex and OpenSpec tooling, and leave the resulting changes in the working tree for review without requiring or mutating GitHub.

## What Changes

- Add a repository-local CLI command that accepts one Markdown task file and runs from the repository root.
- Add a local preflight that verifies Git, Codex, OpenSpec, authentication readiness, task-file safety, and a reviewable starting worktree before model execution.
- Run separate non-interactive Codex planning and implementation stages, with strict OpenSpec validation between them.
- Derive a deterministic issue-independent OpenSpec change name from the task file and reject collisions or unsafe paths rather than overwriting existing changes.
- Validate that planning stays inside the new change directory and that implementation respects protected authority paths and truthful task completion.
- Leave all generated artifacts and implementation edits uncommitted in the current working tree for human inspection; never push, publish, or mutate GitHub.
- Add dry-run/preflight behavior, structured local run records, offline tests, package scripts, and operator documentation.

## Capabilities

### New Capabilities

- `local-ai-openspec-runner`: Defines safe local task intake, separated OpenSpec planning and implementation stages, validation, reviewable outputs, and failure recovery for the repository-local CLI.

### Modified Capabilities

- None.

## Impact

- Adds a dependency-free Node CLI and supporting prompts, schemas, validation helpers, tests, package scripts, and local usage documentation.
- Reuses the installed `codex exec`, OpenSpec 1.12.0, Git, repository skills, and existing validation conventions without adding a GitHub dependency.
- Reads local task files and writes only to the current repository checkout and an ignored local run-state directory.
- Does not replace or modify the existing GitHub Actions delivery workflow, Project lifecycle, pull-request observer, storefront, backend, database, or authentication behavior.
