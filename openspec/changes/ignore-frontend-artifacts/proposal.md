## Why

Frontend development now includes a Next.js workspace under `apps/web`, while the repository still contains the original static storefront files during migration. The ignore rules should keep generated frontend artifacts, local environment files, logs, and tool caches out of version control so future frontend work stays reviewable.

## What Changes

- Update the root `.gitignore` to cover common frontend-generated files for the Next.js/Tailwind workspace.
- Preserve source files, lockfiles, static storefront files, and configuration that should remain tracked.
- Group ignore rules so frontend, backend, OS/editor, environment, and build-cache entries are easy to maintain.

## Capabilities

### New Capabilities

- None. This is a repository hygiene/tooling change with no user-facing behavior.

### Modified Capabilities

- None. No existing product or API requirements change.

## Impact

- Affects the root `.gitignore`.
- Helps avoid accidental tracking of `apps/web/.next/`, TypeScript build info, frontend environment files, dependency folders, logs, coverage output, and similar generated artifacts.
- Does not change runtime frontend behavior, backend APIs, database schema, dependencies, or existing static storefront content.
