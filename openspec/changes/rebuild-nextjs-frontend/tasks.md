## 1. Frontend Scaffold

- [x] 1.1 Create `apps/web` as a Next.js App Router TypeScript project with Tailwind CSS and verify expected app, config, and package files exist.
- [x] 1.2 Add project scripts for development, linting, and production build and verify the scripts are listed in `apps/web/package.json`.
- [x] 1.3 Add root workspace or package configuration only as needed to run the web app cleanly and verify backend project files are not disrupted.
- [x] 1.4 Configure Tailwind global styles, base layout metadata, font choices, color tokens, focus states, and responsive container conventions and verify the app shell renders without the legacy CSS files.
- [x] 1.5 Add frontend environment documentation for `NEXT_PUBLIC_API_BASE_URL` and verify local setup instructions explain the FastAPI dependency.

## 2. API and Session Foundation

- [x] 2.1 Add typed frontend DTOs for backend categories, product pages/details, auth responses, users, listings, watchlist, cart, and API error envelopes and verify TypeScript compilation covers the types.
- [x] 2.2 Implement public API helpers for categories, product listing, category products, product detail, and search and verify each helper targets the documented `/api/v1` route.
- [x] 2.3 Implement protected API helpers for auth, current user, refresh, logout, listing creation/listing management, watchlist, and cart and verify credentialed requests include cookies where required and bearer tokens where required.
- [x] 2.4 Implement frontend auth/session state that keeps access tokens out of long-lived browser storage, restores via refresh, and clears on logout; verify guest and authenticated state transitions can be exercised in the UI.
- [x] 2.5 Add shared loading, error, not-found, and empty-state handling for API-backed views and verify failed or missing API data does not render misleading stale products.

## 3. Shared UI and Motion System

- [x] 3.1 Build the shared layout, header, StockX-style logo, search bar, category navigation, account controls, and footer and verify desktop and mobile navigation states render.
- [x] 3.2 Build `ProductCard`, `ProductGrid`, product media, price/sold-count formatting, breadcrumbs, category hero, and category side navigation/filter components and verify they render seeded product/category API data.
- [x] 3.3 Build accessible auth and marketplace form primitives with labels, validation messages, disabled/submitting states, and backend error display and verify keyboard navigation works through the forms.
- [x] 3.4 Rebuild sticky header and mobile menu behavior with React state and accessible attributes and verify scroll, open, close, focus, and route-change states work without legacy DOM scripts.
- [x] 3.5 Rebuild reveal-on-scroll, card hover motion, home hero ticker, and scroll-to-top behavior using CSS/React/IntersectionObserver and verify `prefers-reduced-motion` reduces non-essential motion.

## 4. Public Marketplace Routes

- [x] 4.1 Implement the home route `/` using API-backed featured/category product sections plus static-source-inspired editorial/promotional sections and verify it no longer contains hardcoded product lists in page markup.
- [x] 4.2 Implement `/category/[slug]` with category hero content, breadcrumbs, sidebar/category navigation, API-backed products, loading/error/empty states, and scroll-to-top behavior; verify `streetwear` and `collectibles` route parity against the old static pages.
- [x] 4.3 Implement `/product/[slug]` with product identity, image, price, category, variants, and auth-aware marketplace actions and verify a seeded backend product renders from its slug.
- [x] 4.4 Implement `/search` with query-driven results, active query display, empty state, and search submission from the header and verify non-empty searches route correctly.
- [x] 4.5 Verify public routes do not depend on `index.html`, `streetwear.html`, `collectibles.html`, `css/`, or `js/` at runtime while leaving those files in the repository.

## 5. Authenticated Workflows

- [x] 5.1 Implement `/login` and `/signup` forms against backend auth endpoints and verify successful submission updates authenticated navigation.
- [x] 5.2 Implement logout from authenticated navigation and verify it calls the backend logout flow and returns the UI to guest state.
- [x] 5.3 Implement `/account` as an authenticated page with current user state plus empty/loading/error states and verify unauthenticated visitors are sent to login or an auth-required state.
- [x] 5.4 Implement `/sell` as an authenticated listing entry flow that selects or references available products, submits listing details to the backend, and verifies successful listing creation or validation errors.
- [x] 5.5 Surface basic watchlist and cart UI where appropriate for product/account flows and verify protected requests remain user-scoped through the backend.

## 6. Verification and Polish

- [x] 6.1 Run frontend formatting/lint/type checks and verify they pass or document any unavailable tool with the reason.
- [x] 6.2 Run the production frontend build and verify it completes successfully.
- [x] 6.3 Run route smoke checks for `/`, `/category/streetwear`, `/category/collectibles`, a seeded `/product/[slug]`, `/search`, `/login`, `/signup`, `/account`, and `/sell` and verify expected page states render.
- [x] 6.4 Verify responsive layout at mobile and desktop widths, including header/search/menu, product grids, category sidebar behavior, forms, and footer, with no overlapping text or controls.
- [x] 6.5 Verify animation behavior for sticky header, mobile menu, reveal-on-scroll, hero ticker, hover motion, scroll-to-top, and reduced-motion mode.
- [x] 6.6 Run or re-run relevant backend API tests/smoke setup if frontend route smoke depends on local API data and verify required seeded categories/products are available.
- [x] 6.7 Update frontend README or project documentation with setup, environment, available routes, API dependency, and static-file parity notes and verify instructions match implemented scripts.
- [x] 6.8 Run `openspec validate rebuild-nextjs-frontend --strict` and verify the change remains valid after implementation updates.
