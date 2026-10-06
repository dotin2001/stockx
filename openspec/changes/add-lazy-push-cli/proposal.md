## Why

Committing and pushing this repo currently requires several manual Git steps, which makes it easy to skip the pre-push sanity check or accidentally publish files that should stay local. A small `lazy push` command can make the common path fast while still stopping when the working tree contains changes that should not be pushed.

## What Changes

- Add a repo-local CLI command named `lazy` with a `push` subcommand invoked as `lazy push "my commit text"`.
- Make `lazy push` inspect Git state before staging and report blockers that would make the current changes unsafe or impossible to push.
- When no blockers are found, run the workflow `git add .`, `git commit -m "<message>"`, and `git push`.
- Ensure command output clearly reports what happened and what the user must fix when the workflow stops.

## Capabilities

### New Capabilities

- `developer-workflow-cli`: Defines repository-local developer workflow commands for safe Git automation.

### Modified Capabilities

- None.

## Impact

- Affects repository developer tooling and documentation for local Git workflow.
- May add a small CLI entry point and npm/package configuration so the command can be invoked predictably from this project.
- Does not change frontend runtime behavior, backend APIs, database schema, auth behavior, or marketplace user flows.
