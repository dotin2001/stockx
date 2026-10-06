## Context

See `proposal.md` for motivation. The repository currently has `apps/web` scaffolded as a Next.js App Router app with React, TypeScript, Tailwind CSS, PostCSS, ESLint, root workspace scripts, route folders for the expected marketplace pages, reusable components, client API helpers, and an auth context that restores sessions through the backend refresh flow.

The prior `rebuild-nextjs-frontend` change appears implemented, but the permanent spec tree only contains `api-smoke-testing`. This change records durable frontend stack standards instead of rebuilding the app again. The legacy static storefront files remain in the root, and `.gitignore` already excludes generated frontend artifacts such as `apps/web/.next/` and TypeScript build info.

## Goals / Non-Goals

**Goals:**

- Make the existing frontend stack contract explicit for future feature and refactor work.
- Confirm the current stack choices: Next.js App Router, React, TypeScript strict mode, Tailwind CSS, ESLint, root workspace scripts, and documented environment setup.
- Standardize API access, auth session handling, shared UI states, responsive/accessibility expectations, and verification commands.
- Identify focused implementation tasks that review and update the current app where it falls short of the new standards.

**Non-Goals:**

- No migration away from the existing Next.js app.
- No backend API redesign, database schema change, or auth protocol change.
- No removal of `index.html`, category static pages, `css/`, or `js/`.
- No broad visual redesign beyond updates needed to preserve accessible, responsive marketplace behavior.
- No new dependency unless a specific gap cannot be solved cleanly with the current stack.

## Decisions

### Keep the current frontend stack

Continue with the existing `apps/web` package using Next.js App Router, React, TypeScript, Tailwind CSS, PostCSS, ESLint, and npm workspaces. The package already exposes `dev`, `lint`, `typecheck`, and `build`, and the root `package.json` wraps those commands as `web:*` scripts.

Alternative considered: introduce a different frontend framework or styling system during this review. That would create churn without solving a current requirement; the existing stack already matches `AGENTS.md`, the local skill guidance, and the implemented route/component shape.

### Treat API access as a typed boundary

Keep a small frontend API module as the boundary between route/components and `/api/v1`. It should own API base URL resolution, error envelope handling, request credentials, bearer-token attachment, and DTO imports. Routes and shared components should consume this boundary instead of constructing fetch calls ad hoc.

Alternative considered: let each route call `fetch` directly. That would make auth, errors, URL handling, and backend response assumptions inconsistent across the app.

### Keep auth state aligned with backend security

Continue using in-memory access-token state and restore sessions via the refresh endpoint with cookies. Login and signup should apply the same session state, protected pages should handle checking/guest/authenticated states, and logout should call the backend logout endpoint before clearing frontend state.

Alternative considered: persist access tokens in browser storage for easier page reload behavior. That conflicts with the backend's HTTP-only refresh-cookie design and increases token exposure.

### Use Tailwind plus shared components as the UI contract

Keep Tailwind as the styling layer and preserve the existing shared components for layout, navigation, product cards/grids, auth forms, protected gates, and UI states. Shared utility classes such as page containers and surfaces are acceptable when they reduce repetition. New routes should avoid copying large blocks of route-specific marketplace markup for repeated surfaces.

Alternative considered: port or re-import the legacy SCSS into the Next.js runtime. The static CSS remains useful as visual reference, but importing it would reintroduce global selector coupling that the componentized app is meant to retire.

### Verify stack changes at both tooling and route levels

Frontend stack updates should run `npm run web:typecheck`, `npm run web:lint`, and `npm run web:build` where possible. Changes touching routing, auth, API helpers, shared components, layout, or motion should also smoke-check the expected route set against a seeded backend or clearly document when local backend prerequisites are unavailable.

Alternative considered: rely only on production build. Build success does not prove route data, auth restore, protected surfaces, or responsive UI behavior still work.

## Risks / Trade-offs

- API/backend availability can block route smoke checks -> Document missing local backend or seed prerequisites when smoke checks cannot run, and keep lint/type/build verification independent.
- Hand-written DTOs can drift from backend schemas -> Keep DTO updates in the same change as frontend API usage updates; consider generated shared types later if drift becomes expensive.
- Client-heavy data loading can limit SSR benefits -> Keep current behavior for now and evaluate server components or route-level data loading later only where it improves user experience without complicating auth.
- Reduced-motion and responsive issues are easy to miss -> Include targeted smoke checks for mobile/desktop layouts and motion preference when shared UI or motion code changes.
- Existing active frontend OpenSpec changes may overlap historically -> Treat this change as the durable standards layer; archive or sync older completed changes separately when the project is ready.

## Migration Plan

1. Review `apps/web` package scripts, config, README, environment notes, and root workspace commands against the new stack standards.
2. Review API helpers and DTOs for central API base URL handling, backend error envelope support, protected request credentials, and bearer-token usage.
3. Review auth context and protected pages for refresh-cookie restore, in-memory access-token handling, guest/authenticated navigation, and logout state clearing.
4. Review shared UI components, Tailwind tokens, responsive layouts, focus states, loading/error/empty states, and reduced-motion behavior.
5. Update only the frontend files and documentation needed to satisfy the standards.
6. Run frontend typecheck, lint, and build checks; run route smoke checks when backend prerequisites are available.

Rollback is a normal code rollback for frontend/documentation updates. Since this change should not alter backend contracts, schema, or static-file retention, no backend or database rollback is expected.
