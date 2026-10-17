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
store inventory, cart, watchlist, customer message, and admin message data. Start the backend and seed PostgreSQL using
the instructions in `apps/api/README.md`.

## Environment

Create `apps/web/.env.local` when the API is not running at the default local
URL. By default the frontend uses its current hostname with port `8000`, so
`http://localhost:3000` calls `http://localhost:8000` and
`http://127.0.0.1:3000` calls `http://127.0.0.1:8000`:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Keep the frontend and API hostnames aligned (`localhost` with `localhost`, or
`127.0.0.1` with `127.0.0.1`). The refresh token is an HTTP-only cookie, and
matching hostnames allow the authenticated session to be restored after Stripe
redirects the browser back to the storefront.

The backend should allow the frontend origin in `CORS_ORIGINS`, for example:

```text
CORS_ORIGINS=http://localhost:3000
```

## Data Contract Notes

Catalog, search, product detail, account, cart, watchlist, customer message, and admin message data flow
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
/checkout
/orders
/orders/[id]
/sell
/admin/messages
/admin/products
/admin/products/new
```

`/checkout`, `/orders`, and `/orders/[id]` are authenticated customer routes.
Guest checkout preserves `/checkout` as the post-authentication destination so
the existing guest-cart merge completes first. The checkout page can always
review an available account cart; confirmation is enabled only when the API is
running with `CHECKOUT_MODE=manual` or a fully configured `stripe` mode. Manual
confirmations are clearly shown as unpaid. Stripe mode redirects the browser to
the server-returned `checkout.stripe.com` URL; the frontend never receives a
secret key or raw card details.

Stripe success and cancel query parameters are explanatory only. Order detail
loads authenticated server state, briefly polls after a return, and renders
pending, processing, paid, failed, expired, or cancelled from the order's safe
payment-attempt summary. An open session can be resumed; cancellation is an
explicit owner-scoped action. Returning from Stripe never marks an order paid.

`/admin/products` is the primary product management route for authenticated
admins. It lists active and archived catalog products, exposes catalog edit and
variant controls for normal admins and supreme admins, and shows listing
inventory summaries. `/admin/products/new` remains reachable from that page and
creates catalog products through the backend admin API. Supreme admins also see
quantity and inventory status controls; normal admins can read inventory state
but cannot mutate quantity or listing status. `/admin/messages` is visible to
admins for customer messages. `/sell` is intentionally informational: normal
users are customers with cart, watchlist, and message-admin account actions,
while store admins manage catalog and sellable inventory.

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
npm run web:test
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
