## Why

The current storefront is a set of static HTML/CSS/JS pages with hardcoded product markup and direct DOM scripts, while the backend now exposes real catalog, auth, listing, watchlist, cart, and admin APIs. Rebuilding the frontend in Next.js, TypeScript, and Tailwind CSS turns the existing visual direction into a maintainable, data-driven marketplace app and lets the backend foundation become visible to users.

## What Changes

- Scaffold `apps/web` as a Next.js App Router application using TypeScript and Tailwind CSS.
- Migrate the static storefront experience into reusable React components for the header, search bar, category navigation, product cards, product grids, category pages, product detail, auth forms, account, sell/listing, cart, watchlist, and shared states.
- Preserve the existing StockX-style visual language from `index.html`, `streetwear.html`, `collectibles.html`, `css/`, and `js/`, while modernizing responsive layout, accessibility, and route behavior.
- Replace hardcoded product lists in page markup with API-backed data from the FastAPI backend.
- Keep or improve the current animation behaviors: sticky header, mobile menu transition, reveal-on-scroll sections, scroll-to-top affordance, card hover motion, and marquee-style hero motion using accessible React/Tailwind patterns.
- Add frontend verification for lint/type/build and route smoke coverage once the app is scaffolded.
- Keep the existing static files until the Next.js routes reach useful route and content parity.

## Capabilities

### New Capabilities

- `nextjs-marketplace-frontend`: Defines the user-facing Next.js marketplace frontend, including route parity, data-driven catalog/search/product views, auth-aware navigation and protected pages, and preserved or upgraded animation behavior.

### Modified Capabilities

- None.

## Impact

- Affected code: new `apps/web` frontend, root package/workspace configuration if needed, and frontend documentation.
- Affected APIs: consumes existing FastAPI routes under `/api/v1` for categories, products, search, auth, listings, watchlist, and cart; no backend API contract changes are planned.
- Dependencies: introduces Next.js, React, TypeScript, Tailwind CSS, frontend lint/build tooling, and likely a small icon package such as `lucide-react`.
- Migration: static files remain in place until the Next.js implementation reaches useful parity with the current home, streetwear, and collectibles experiences.
