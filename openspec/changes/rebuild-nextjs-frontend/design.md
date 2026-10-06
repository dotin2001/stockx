## Context

See `proposal.md` for motivation. The repository currently has static storefront pages at `index.html`, `streetwear.html`, and `collectibles.html`, shared styles in `css/`, and DOM scripts in `js/`. There is no `apps/web` scaffold yet. The backend already exposes public catalog/search/product routes, auth session routes, and protected listings/watchlist/cart routes under `/api/v1`; protected calls use bearer access tokens, and refresh uses the HTTP-only `stockx_refresh` cookie.

The static source has useful behavior to preserve: StockX-style header/search/category navigation, category hero imagery, product cards and grids, sidebar category filters, mobile menu toggling, sticky header behavior, scroll-to-top on category pages, reveal-on-scroll sections, hover motion, and a marquee-style hero message.

## Goals / Non-Goals

**Goals:**

- Create `apps/web` as the primary Next.js App Router frontend.
- Reach useful route parity for `/`, `/category/[slug]`, `/product/[slug]`, `/search`, `/login`, `/signup`, `/account`, and `/sell`.
- Build reusable, typed components rather than copying static page markup.
- Consume the existing FastAPI API contracts without requiring backend changes.
- Preserve the current marketplace feel and improve responsiveness, accessibility, and animation implementation.
- Keep legacy static files available until the new app reaches useful parity.

**Non-Goals:**

- No checkout/payment flow.
- No broad admin dashboard in this change.
- No backend API redesign unless implementation reveals a blocking frontend contract gap.
- No full visual redesign that abandons the current StockX-style storefront direction.
- No removal of the static files during initial migration.

## Decisions

### Scaffold `apps/web` as a standalone Next.js app inside the repo

Use `apps/web` with App Router, TypeScript, Tailwind CSS, and project-local package scripts for `dev`, `lint`, and `build`. Add root workspace/package configuration only as needed to run the web app cleanly from the repo.

Alternative considered: incrementally enhance the static HTML. That would keep duplicated page markup, hardcoded product data, and direct DOM manipulation, and would not line up with the planned full-stack direction.

### Model API contracts in the frontend

Add typed API helpers for the backend response shapes used by the frontend:

- categories
- product summaries/pages/details
- auth responses/current user
- listings
- watchlist
- cart
- standard error envelope

Use a single `NEXT_PUBLIC_API_BASE_URL` setting with a local default such as `http://127.0.0.1:8000`. Requests that need refresh cookies must include credentials. Protected requests attach the current bearer access token.

Alternative considered: generate shared types from backend schemas immediately. That can be useful later, but there is no generation pipeline yet; hand-written frontend DTOs keep this migration focused.

### Keep access tokens out of long-lived browser storage

Use an auth provider or equivalent session module that stores the access token in memory, restores sessions by calling the refresh endpoint with credentials, then calls current-user endpoints with the new bearer token. Login/signup update the same session state; logout calls the backend logout route and clears frontend auth state.

Alternative considered: store access tokens in `localStorage`. That makes restore simpler but increases exposure to XSS and conflicts with the backend's HTTP-only refresh-cookie design.

### Build the UI from data-driven marketplace components

Create reusable components for layout and repeated marketplace surfaces:

- `Header`, `SearchBar`, `CategoryNav`, and navigation/account controls
- `ProductCard`, `ProductGrid`, `ProductDetail`, and product media helpers
- `CategoryHero`, category side navigation/filter blocks, breadcrumbs
- `AuthForm`, protected route states, `AccountSummary`, and sell/listing form
- `EmptyState`, `LoadingState`, and `ErrorState`
- animation wrappers/hooks for reveal-on-scroll and reduced motion handling

The static page sections should become data-driven blocks. Home can initially group products from backend category/search/list responses rather than embedding hardcoded lists in JSX.

Alternative considered: migrate each static page as one large route component. That reaches pixels faster but preserves duplication and makes route parity brittle.

### Implement animations with React state, CSS, and browser observers

Translate the old animation scripts into route-safe frontend behavior:

- sticky header: scroll listener or CSS state isolated inside `Header`
- mobile menu: React state with aria-expanded, focus-visible styles, and escape/route-close behavior where practical
- reveal-on-scroll: IntersectionObserver hook with Tailwind transition classes
- hero ticker: CSS animation or controlled ticker component instead of `<marquee>`
- scroll-to-top: client component shown after threshold on long pages
- hover motion: Tailwind transform/transition utilities on cards and buttons
- reduced motion: honor `prefers-reduced-motion`

Avoid adding a large motion library for the first pass. Add one later only if interactions become too complex for CSS and IntersectionObserver.

Alternative considered: reuse `js/index.js` and `js/product.js`. Those scripts query global DOM classes and do not fit React routing, server rendering, cleanup, or accessibility needs.

### Use Tailwind utilities with small component-level conventions

Use Tailwind for layout, spacing, typography, states, and responsive behavior. Keep cards at restrained radii, maintain readable marketplace density, and avoid a marketing landing-page redesign. Shared component classes can be introduced only where they reduce meaningful repetition.

Alternative considered: port the existing SCSS as-is. That would bring old selectors and duplicated responsive rules into a new component system, making future maintenance harder.

### Use accessible icons and media handling

Use `lucide-react` icons for common controls where helpful, and retain the StockX-style wordmark as an inline component or accessible SVG asset. Product and category images should use meaningful alt text. Configure remote image hosts if using Next image optimization; otherwise start with normal images and move to optimized images once remote patterns are stable.

Alternative considered: keep Font Awesome CDN. A CDN stylesheet is unnecessary for a bundled Next app and complicates loading and icon consistency.

## Risks / Trade-offs

- API and frontend dev servers have different origins -> Configure API CORS and frontend `NEXT_PUBLIC_API_BASE_URL`; include credentials for refresh/logout calls.
- In-memory access token is lost on refresh -> Restore through the backend refresh endpoint on app load and handle unauthenticated fallback cleanly.
- Backend has no dedicated frontend aggregation endpoint -> Keep pages simple and use existing catalog/search routes; avoid requiring backend changes unless a route cannot meet a required user flow.
- Remote product images come from many hosts -> Prefer image configuration with explicit remote patterns where feasible; use a safe fallback image state when an image fails.
- Animations can hurt accessibility or performance -> Use IntersectionObserver, CSS transitions, and `prefers-reduced-motion`; avoid expensive scroll work and layout thrashing.
- Static category pages contain more hardcoded products than current seed data may expose -> Plan route/content parity around API-backed seeded content first, then add seed/API coverage in a separate backend/database change if frontend parity requires more catalog records.
- Next.js setup introduces new repository tooling -> Keep scripts documented and scoped so backend commands continue working independently.

## Migration Plan

1. Scaffold `apps/web` and install/configure the Next.js, TypeScript, Tailwind, lint, and build toolchain.
2. Add environment configuration and typed API helpers for public and protected backend routes.
3. Implement shared layout, navigation, product, state, and animation primitives.
4. Build public routes for home, categories, product detail, and search from backend data.
5. Build auth routes and session restoration using the backend auth contract.
6. Build protected account and sell/listing flows, plus basic watchlist/cart surfaces if backend data is exposed in the UI during this pass.
7. Verify lint, type/build, responsive rendering, route smoke behavior, auth restore/logout, and animation/reduced-motion behavior.
8. Keep static files in place and document the parity status. Remove or archive them only in a later cleanup change after route and content parity is accepted.

Rollback is code rollback for the new `apps/web` and package configuration. Because this change should not alter backend schema or API contracts, backend rollback is not expected.
