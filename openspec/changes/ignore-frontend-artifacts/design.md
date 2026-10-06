## Context

See `proposal.md` for motivation. The repository currently has a root `.gitignore` with backend caches, `node_modules/`, `apps/web/.next/`, `apps/web/tsconfig.tsbuildinfo`, and `apps/web/.env.local`. The frontend workspace is a Next.js 15 app under `apps/web` managed through npm workspaces, while legacy static HTML/CSS/JS files remain in the repository during migration.

## Goals / Non-Goals

**Goals:**

- Keep generated frontend output, local-only environment files, logs, cache directories, and package-manager byproducts ignored.
- Keep source files, package manifests, lockfiles, static storefront files, and app configuration eligible for tracking.
- Organize ignore rules into readable sections so later frontend/backend additions are easy to review.

**Non-Goals:**

- Do not remove already tracked files from Git history.
- Do not change build scripts, dependencies, runtime configuration, or application code.
- Do not ignore broad source directories such as `apps/web/`, `css/`, or `js/`.

## Decisions

- Use the root `.gitignore` as the single ignore policy for the workspace.
  - Rationale: the repository already has a root ignore file and npm workspaces are configured from the root.
  - Alternative considered: add `apps/web/.gitignore`; rejected because duplicate local policy would be easier to drift.
- Ignore generated artifacts by category rather than by one-off discovery only.
  - Rationale: entries like `.next/`, `out/`, `coverage/`, `*.tsbuildinfo`, logs, and local env files cover common Next.js/Tailwind development outputs without hiding source.
  - Alternative considered: only add currently observed missing paths; rejected because routine frontend commands would still create review noise later.
- Keep lockfiles tracked.
  - Rationale: `package-lock.json` exists at the repository root and is important for repeatable npm workspace installs.
  - Alternative considered: ignore all lockfiles; rejected because this project is an application, not a published library.

## Risks / Trade-offs

- Overly broad ignore patterns could hide useful source or configuration files. -> Use targeted patterns and explicitly avoid ignoring app/source directories.
- Generated files already tracked would remain tracked even after ignore updates. -> Implementation should check `git status --ignored --short` and call out any tracked generated files separately if found.
- Tooling may introduce new artifact directories later. -> Keep grouped sections easy to extend in follow-up changes.

## Migration Plan

1. Update the root `.gitignore` with organized frontend, backend, environment, OS/editor, log, coverage, and cache sections.
2. Verify that source/config files remain visible to Git and generated frontend artifacts are ignored.
3. Do not delete or untrack files as part of this change unless a later implementation request explicitly asks for cleanup.

## Open Questions

None.
