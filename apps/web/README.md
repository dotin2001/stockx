# StockX Web

Next.js, TypeScript, and Tailwind CSS frontend for the StockX-style store.

## Setup

From the repository root:

```bash
npm install
npm run web:dev
```

Use Node.js `>=18.18.0`; the Next.js build will fail on older Node 18
releases.

The frontend expects the FastAPI backend to be available for catalog, auth,
store inventory, watchlist, cart, and customer message data. Start the backend and seed PostgreSQL using
the instructions in `apps/api/README.md`.

## Environment

Create `apps/web/.env.local` when the API is not running at the default local
URL:

```text
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

The backend should allow the frontend origin in `CORS_ORIGINS`, for example:

```text
CORS_ORIGINS=http://localhost:3000
```

## Data Contract Notes

Catalog, search, product detail, account, customer message, watchlist, and cart data flow
through `apps/web/lib/api.ts` and typed DTOs in `apps/web/lib/types.ts`.
Category navigation labels, hero images, and filter chips are curated frontend
metadata for wayfinding; product records, prices, sold counts, variants, and
pagination still come from the backend API.

## Routes

```text
/
/category/[slug]
/product/[slug]
/search
/login
/signup
/account
/sell
/admin/messages
/admin/products/new
```

`/admin/products/new` is visible to authenticated admins and creates catalog
products through the backend admin API. `/admin/messages` is visible to admins
for customer messages. `/sell` is intentionally informational: normal users are
customers, while store admins manage catalog and sellable inventory. Supreme
admin behavior is deferred to a later change.

Seeded route examples:

```text
/category/streetwear
/category/collectibles
/product/jordan-1-retro-high-element-gore-tex-black-particle-grey
/search?q=jordan
```

## Verification

```bash
npm run web:typecheck
npm run web:lint
npm run web:build
```

The legacy static files remain in the repository during migration:

```text
index.html
streetwear.html
collectibles.html
css/
js/
```

The Next.js app does not import those files at runtime; they are retained as
visual/content parity references until a later cleanup change.
