# StockX Web

Next.js, TypeScript, and Tailwind CSS frontend for the StockX-style marketplace.

## Setup

From the repository root:

```bash
npm install
npm run web:dev
```

The frontend expects the FastAPI backend to be available for catalog, auth,
listing, watchlist, and cart data. Start the backend and seed PostgreSQL using
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
```

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
