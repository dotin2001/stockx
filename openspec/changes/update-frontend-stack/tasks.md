## 1. Stack and Documentation Review

- [x] 1.1 Review `package.json`, `apps/web/package.json`, `apps/web/README.md`, and frontend config files against the stack standards; verify the supported commands, API environment variable, backend/CORS notes, and static-file migration notes are present or list the exact missing updates.
- [x] 1.2 Update frontend/root documentation or scripts only where the review finds drift from the supported `web:dev`, `web:lint`, `web:typecheck`, and `web:build` workflow; verify the documented commands match the implemented package scripts.
- [x] 1.3 Review `.gitignore` and current frontend generated files for stack hygiene; verify generated artifacts such as `.next`, TypeScript build info, logs, coverage, and local env files are ignored while frontend source/config files remain trackable.

## 2. API and Auth Stack Standards

- [x] 2.1 Review `apps/web/lib/api.ts` and `apps/web/lib/types.ts` for centralized API base URL handling, backend error envelope handling, typed DTO coverage, credentialed refresh/logout calls, and bearer-token protected calls; verify any needed corrections are implemented and TypeScript-visible.
- [x] 2.2 Review route/client components for ad hoc API calls or hardcoded catalog records in page markup; verify marketplace catalog/search/product data flows through the shared API boundary or document any deliberate exception.
- [x] 2.3 Review `apps/web/contexts/auth-context.tsx`, protected account/sell surfaces, and authenticated navigation for refresh-cookie restore, in-memory access-token handling, guest/authenticated states, and logout clearing; verify any needed corrections are visible in the UI state flow.

## 3. UI Conventions and Route Behavior

- [x] 3.1 Review shared layout, navigation, search, category navigation, product card/grid, auth form, protected gate, loading, error, and empty-state components for reuse across expected routes; verify duplicated route-specific markup is consolidated or explicitly justified.
- [x] 3.2 Review Tailwind tokens, global styles, focus states, responsive grids, forms, header/search/menu behavior, and footer layout at mobile and desktop sizes; verify updates avoid overlapping text or controls.
- [x] 3.3 Review reveal, ticker, hover, scroll-to-top, and menu motion behavior for `prefers-reduced-motion`; verify non-essential motion is reduced while content and actions remain available.
- [x] 3.4 Verify the Next.js app does not import or depend on `index.html`, category static pages, `css/`, or `js/` at runtime while those legacy files remain in the repository as migration references.

## 4. Verification

- [x] 4.1 Run `npm run web:typecheck` and verify it passes or document the exact blocking issue.
- [x] 4.2 Run `npm run web:lint` and verify it passes or document the exact blocking issue.
- [x] 4.3 Run `npm run web:build` and verify it passes or document the exact blocking issue.
- [x] 4.4 Smoke-check `/`, `/category/streetwear`, `/category/collectibles`, a seeded `/product/[slug]`, `/search`, `/login`, `/signup`, `/account`, and `/sell` against a seeded backend when available; verify expected loading/error/empty/auth states render or document unavailable backend prerequisites.
  - Backend prerequisite unavailable locally: `curl -A codex -sS -m 3 http://127.0.0.1:8000/api/v1/categories` failed because port `8000` was not accepting connections, so seeded API-backed route smoke checks were not run.
- [x] 4.5 Run `openspec validate update-frontend-stack --strict` and verify the OpenSpec change remains valid after implementation updates.
