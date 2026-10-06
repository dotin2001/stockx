## Why

The working tree recently included enough generated or local files to make the GitHub push scope feel risky. Before pushing, the repository needs a deliberate audit so only necessary source, configuration, lockfile, and OpenSpec files are included while generated artifacts, dependencies, local environments, and caches stay out.

## What Changes

- Add an implementation workflow that inventories Git-visible and ignored files before any commit or push.
- Define the expected GitHub-eligible set for the current work: root npm workspace files, `apps/web` source/config files, relevant OpenSpec artifacts, and `.gitignore` updates.
- Define exclusions for local-only files such as `.env` files, virtual environments, dependency installs, Python caches, build output, logs, and coverage reports.
- Require an explicit review of the candidate file list before staging, committing, or pushing.

## Capabilities

### New Capabilities

- None. This is a repository hygiene and release-preparation workflow with no user-facing behavior.

### Modified Capabilities

- None. No existing marketplace, API, database, or auth requirements change.

## Impact

- Affects Git workflow only: status review, ignored-file checks, candidate file list generation, and optional cleanup recommendations.
- Does not modify frontend runtime behavior, backend APIs, database schema, or application dependencies.
- Does not push to GitHub automatically; a push remains a separate explicit action after review.
