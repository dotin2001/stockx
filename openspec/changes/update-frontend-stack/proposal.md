## Why

The frontend is no longer only a planned static-to-Next.js migration: `apps/web` now exists with Next.js App Router, TypeScript, Tailwind CSS, API helpers, auth state, route parity, and build scripts. The project needs an explicit frontend stack contract so future work hardens the current app consistently instead of drifting back into ad hoc page code, untyped API calls, or undocumented tooling choices.

## What Changes

- Formalize the supported frontend stack as Next.js App Router, React, TypeScript, Tailwind CSS, ESLint, and root workspace scripts for `dev`, `lint`, `typecheck`, and `build`.
- Require frontend routes and reusable components to remain data-driven through the FastAPI API contract rather than embedding catalog records in page markup.
- Standardize client API access around typed DTOs, one configurable API base URL, explicit credential handling for refresh/logout, and bearer tokens for protected calls.
- Require the auth/session model to keep access tokens out of long-lived browser storage and restore sessions through the backend refresh-cookie flow.
- Tighten UI stack expectations for shared Tailwind tokens, responsive marketplace layouts, accessible forms/navigation, loading/error/empty states, and reduced-motion behavior.
- Add verification expectations for lint, typecheck, production build, route smoke checks, and documentation updates whenever frontend stack changes are applied.
- Keep the legacy static storefront files as migration references until a later cleanup change explicitly removes them.

## Capabilities

### New Capabilities

- `frontend-stack-standards`: Defines the supported frontend stack, API/session integration standards, UI conventions, and verification requirements for the marketplace web app.

### Modified Capabilities

- None.

## Impact

- Affected code: `apps/web` package/configuration, `apps/web/app`, `apps/web/components`, `apps/web/contexts`, `apps/web/hooks`, `apps/web/lib`, frontend README, and root workspace scripts.
- Affected behavior: no backend API contract changes are planned; frontend behavior should become more consistent, documented, and verifiable.
- Dependencies: confirms the existing Next.js, React, TypeScript, Tailwind, PostCSS, ESLint, and Next ESLint stack; any additional dependency must be justified by an actual frontend need.
- Migration: static HTML/CSS/JS files remain in the repository as parity references and are not removed by this change.
