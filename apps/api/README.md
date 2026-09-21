# StockX API

This workspace contains the FastAPI backend for the marketplace. It exposes versioned API routes, email/password auth, public catalog/search endpoints, admin product management, protected listing/watchlist/cart actions, and the PostgreSQL database foundation.

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
```

`DATABASE_URL` is consumed by the FastAPI app, Alembic, and seed command. The
`POSTGRES_*` variables in `.env.example` are for Docker Compose's PostgreSQL
container and are intentionally ignored by the API settings loader.

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

The seed command is idempotent by category and product slug.

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

Protected marketplace actions:

```text
GET    /api/v1/listings
POST   /api/v1/listings
POST   /api/v1/listings/{id}/cancel
GET    /api/v1/watchlist
POST   /api/v1/watchlist
DELETE /api/v1/watchlist/{id}
GET    /api/v1/cart
POST   /api/v1/cart/items
PATCH  /api/v1/cart/items/{id}
DELETE /api/v1/cart/items/{id}
```

Admin product management:

```text
GET    /api/v1/admin/listings
POST   /api/v1/admin/listings/{id}/cancel
GET    /api/v1/admin/products
POST   /api/v1/admin/products
PATCH  /api/v1/admin/products/{id}
POST   /api/v1/admin/products/{id}/archive
POST   /api/v1/admin/products/{id}/restore
POST   /api/v1/admin/products/{id}/variants
PATCH  /api/v1/admin/product-variants/{id}
DELETE /api/v1/admin/product-variants/{id}
```

Protected routes require an access token:

```text
Authorization: Bearer <access_token>
```

Refresh tokens are stored in the `stockx_refresh` HTTP-only cookie by default and are rotated on refresh.

## Admin Bootstrap

Create a normal user through the API first, then promote that existing user from
the backend environment:

```bash
cd apps/api
python -m app.admin promote admin@example.com
```

If the package is installed in editable mode, the console script is equivalent:

```bash
stockx-api-admin promote admin@example.com
```

The promotion command normalizes the email, requires the user to already exist,
does not ask for or change passwords, and leaves refresh-token records intact.

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

The default `pytest` suite uses in-process test clients and does not require a
running API server.

## Running-Service API Smoke Test

Use the smoke test when you want to verify the running FastAPI service,
PostgreSQL-backed seed data, refresh cookies, auth flows, listing creation,
seller listing management, watchlist/cart behavior, admin bootstrap, admin
listing management, and admin archive/restore behavior through real HTTP
requests.

From the repository root, start PostgreSQL:

```bash
docker compose -f infra/docker/docker-compose.yml --env-file apps/api/.env.example up -d postgres
```

Prepare the database and start the API:

```bash
cd apps/api
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload
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
because of previous user data. Listings, cart rows, and revoked refresh-token
rows created by smoke runs may remain in the local database. The admin smoke
promotes a temporary smoke user, temporarily archives the seeded product,
verifies archived-product listing rejection, and restores the product before
finishing. To reset local smoke data, use the optional rollback above and then
re-run migrations and seed data.

Common smoke-test failures:

- `Could not connect to API`: start `uvicorn app.main:app --reload`, or pass the
  correct `--base-url`.
- Missing seeded categories or product: run `alembic upgrade head` and
  `python -m app.db.seed` against the same database used by the running API.
- Refresh cookie assertions fail over local HTTP: confirm
  `REFRESH_COOKIE_SECURE=false`.

Quick manual API smoke:

```bash
uvicorn app.main:app --reload
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/categories
curl "http://localhost:8000/api/v1/search?q=jordan"
```
