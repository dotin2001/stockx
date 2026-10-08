# StockX API

This workspace contains the FastAPI backend for the store-owned selling site. It exposes versioned API routes, email/password auth, public catalog/search endpoints, admin product management, protected customer cart/watchlist/message actions, admin-managed listings used as store inventory, and the PostgreSQL database foundation.

## Setup

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Start PostgreSQL from the repository root:

```bash
docker compose -f infra/docker/docker-compose.yml --env-file apps/api/.env.example up -d postgres
```

Important environment variables:

```text
DATABASE_URL=postgresql+psycopg://stockx:stockx@localhost:5432/stockx
SECRET_KEY=change-me-in-local-env
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
REFRESH_COOKIE_NAME=stockx_refresh
REFRESH_COOKIE_SECURE=false
REFRESH_COOKIE_SAMESITE=lax
CORS_ORIGINS=http://localhost:3000
CHECKOUT_MODE=disabled
```

`DATABASE_URL` is consumed by the FastAPI app, Alembic, and seed command. The
`POSTGRES_*` variables in `.env.example` are for Docker Compose's PostgreSQL
container and are intentionally ignored by the API settings loader.

`CHECKOUT_MODE` accepts only `disabled` and `manual` and defaults to
`disabled`. Use `CHECKOUT_MODE=manual` only for local development when you
explicitly want confirmation to create an unpaid order and consume inventory.
No payment provider is contacted by manual checkout.

## Migrations

```bash
cd apps/api
alembic upgrade head
alembic downgrade base
```

## Seed Data

```bash
cd apps/api
python -m app.db.seed
```

The catalog seed is idempotent by category and product slug and creates five
configured products in each of Sneakers, Streetwear, and Collectibles. It does
not create a user or inventory owner.

After registering and promoting an existing admin account, seed one active
quantity-10 inventory listing for every configured product:

```bash
python -m app.admin promote admin@example.com
python -m app.db.seed --inventory-owner-email admin@example.com
```

Inventory seeding uses deterministic `SEED-...` purchase-option SKUs. Running
the command again for the same admin does not create duplicates, but it resets
the managed demo listings to their configured USD price, active status, and
quantity. Unrelated administrator-created variants and listings are preserved.

## API Routes

Health:

```text
GET    /health
```

Auth:

```text
POST   /api/v1/auth/register
POST   /api/v1/auth/login
GET    /api/v1/auth/me
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
```

Catalog:

```text
GET    /api/v1/categories
GET    /api/v1/products
GET    /api/v1/categories/{slug}/products
GET    /api/v1/products/{slug}
GET    /api/v1/search?q=...
```

Protected customer actions:

```text
GET    /api/v1/watchlist
POST   /api/v1/watchlist
DELETE /api/v1/watchlist/{id}
GET    /api/v1/cart
POST   /api/v1/cart/items
PATCH  /api/v1/cart/items/{id}
DELETE /api/v1/cart/items/{id}
GET    /api/v1/messages
POST   /api/v1/messages
GET    /api/v1/messages/{id}
GET    /api/v1/checkout/summary
POST   /api/v1/orders
GET    /api/v1/orders
GET    /api/v1/orders/{id}
```

`POST /api/v1/orders` requires an `Idempotency-Key` header. The request body
contains the server-issued checkout token plus recipient/contact/address data;
product lines and totals are always recalculated from the current account cart.
Orders created in manual mode are `confirmed` and `unpaid`.

Guests can browse public catalog data and add active sellable items to a guest
cart. Watchlist and message-admin actions require an authenticated customer.

Normal admin store management:

```text
GET    /api/v1/listings
POST   /api/v1/listings
POST   /api/v1/listings/{id}/cancel
GET    /api/v1/admin/listings
POST   /api/v1/admin/listings/{id}/cancel
POST   /api/v1/admin/listings/{id}/inventory/quantity
PATCH  /api/v1/admin/listings/{id}/inventory/status
GET    /api/v1/admin/messages
GET    /api/v1/admin/messages/{id}
POST   /api/v1/admin/messages/{id}/read
GET    /api/v1/admin/products
POST   /api/v1/admin/products
PATCH  /api/v1/admin/products/{id}
POST   /api/v1/admin/products/{id}/archive
POST   /api/v1/admin/products/{id}/restore
POST   /api/v1/admin/products/{id}/variants
PATCH  /api/v1/admin/product-variants/{id}
DELETE /api/v1/admin/product-variants/{id}
```

Supreme-admin user management:

```text
GET    /api/v1/admin/users
POST   /api/v1/admin/users/promote
POST   /api/v1/admin/users/{id}/promote
POST   /api/v1/admin/users/{id}/demote
```

`GET /api/v1/admin/products` returns catalog products with inventory summaries
and listing-level inventory items for admin product management. Normal admins
can read these summaries and manage catalog product fields, archive/restore
state, and variants. Listing inventory has durable `available_quantity`; public
cart flows only accept active listings with quantity greater than zero and
reject cart quantities above availability. Quantity adjustments and inventory
status changes under `/api/v1/admin/listings/{id}/inventory/*` require a
supreme admin.

Protected routes require an access token:

```text
Authorization: Bearer <access_token>
```

Refresh tokens are stored in the `stockx_refresh` HTTP-only cookie by default and are rotated on refresh.

## Admin Bootstrap

Create a normal user through the API first, then promote that existing user from
the backend environment. Normal admins can manage catalog products, store
listings/inventory, and customer messages:

```bash
cd apps/api
python -m app.admin promote admin@example.com
```

If the package is installed in editable mode, the console script is equivalent:

```bash
stockx-api-admin promote admin@example.com
```

Supreme admins can also manage normal-admin access through
`/api/v1/admin/users`. Grant supreme-admin status only from the backend
environment:

```bash
cd apps/api
python -m app.admin promote-supreme supreme@example.com
```

If the package is installed in editable mode, the console script is equivalent:

```bash
stockx-api-admin promote-supreme supreme@example.com
```

Both promotion commands normalize the email, require the user to already exist,
do not ask for or change passwords, and leave refresh-token records intact.
`promote-supreme` sets both `users.is_admin` and `users.is_supreme_admin`.
In-app user management can promote or demote normal-admin access, but it cannot
grant or remove supreme-admin status.

## Verification

```bash
cd apps/api
pytest
alembic upgrade head
python -m app.db.seed
python -m app.db.seed
```

Optional destructive local rollback:

```bash
alembic downgrade base
```

The checkout migration adds `orders` and `order_items`. Disable checkout and
back up any order data that must be retained before downgrading past that
revision because the downgrade drops those tables.

The default `pytest` suite uses in-process test clients and does not require a
running API server.

## Running-Service API Smoke Test

Use the smoke test when you want to verify the running FastAPI service,
PostgreSQL-backed seed data, refresh cookies, auth flows, admin-created store
listings, guest/authenticated cart behavior, authenticated watchlist/customer
messages, admin bootstrap, admin
listing management, admin archive/restore behavior, manual checkout, inventory
decrement, cart clearing, order history/detail, and cross-user nondisclosure
through real HTTP requests.

From the repository root, start PostgreSQL:

```bash
docker compose -f infra/docker/docker-compose.yml --env-file apps/api/.env.example up -d postgres
```

Prepare the database and start the API:

```bash
cd apps/api
alembic upgrade head
python -m app.db.seed
CHECKOUT_MODE=manual uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd apps/api
python -m app.smoke --base-url http://127.0.0.1:8000
```

If the package is installed in editable mode, the console script is equivalent:

```bash
stockx-api-smoke --base-url http://127.0.0.1:8000
```

You can also set the base URL with `STOCKX_API_BASE_URL`:

```bash
STOCKX_API_BASE_URL=http://127.0.0.1:8000 python -m app.smoke
```

For local HTTP smoke tests, keep `REFRESH_COOKIE_SECURE=false` so the refresh
cookie can round-trip over `http://127.0.0.1:8000`.

The smoke test expects seeded categories `sneakers`, `streetwear`, and
`collectibles`, plus the seeded Jordan product slug
`jordan-1-retro-high-element-gore-tex-black-particle-grey`. It creates a unique
`api-smoke-...@example.test` users on every run, so repeated runs do not fail
because of previous user data. Listings, messages, cart rows, and revoked
refresh-token rows created by smoke runs may remain in the local database. The
admin smoke promotes a temporary smoke user, temporarily archives the seeded
product, verifies archived-product listing rejection, and restores the product
before finishing. To reset local smoke data, use the optional rollback above and
then re-run migrations and seed data.

Common smoke-test failures:

- `Could not connect to API`: start `uvicorn app.main:app --reload`, or pass the
  correct `--base-url`.
- Missing seeded categories or product: run `alembic upgrade head` and
  `python -m app.db.seed` against the same database used by the running API.
- Refresh cookie assertions fail over local HTTP: confirm
  `REFRESH_COOKIE_SECURE=false`.
- Manual checkout prerequisite failure: restart the API with
  `CHECKOUT_MODE=manual`. The smoke flow intentionally fails when order
  placement remains disabled.

Stripe Checkout Sessions, charges, payment attempts, webhooks, refunds, and
fulfillment remain deferred. The order foundation is provider-independent and
the manual local flow never represents an order as paid.

Quick manual API smoke:

```bash
uvicorn app.main:app --reload
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/categories
curl "http://localhost:8000/api/v1/search?q=jordan"
```
