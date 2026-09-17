# Database Foundation

The first database foundation lives in `apps/api` and uses PostgreSQL, SQLAlchemy 2.x models, and Alembic migrations.

## Local PostgreSQL

```bash
docker compose -f infra/docker/docker-compose.yml --env-file apps/api/.env.example up -d postgres
```

The default development connection URL is:

```text
postgresql+psycopg://stockx:stockx@localhost:5432/stockx
```

Copy `apps/api/.env.example` to `apps/api/.env` for local overrides. Do not commit secret values.

## Schema Summary

Initial tables:

- `users`: account identity, unique email, password hash, `is_admin BOOLEAN NOT NULL DEFAULT FALSE`, timestamps.
- `refresh_tokens`: hashed refresh tokens with expiration, revocation, and replacement linkage.
- `categories`: unique category slugs.
- `products`: required category ownership, unique product slugs, display fields, image URL, integer `lowest_ask_cents`, and sold count.
- `product_variants`: optional size, color, and SKU per product.
- `listings`: user-owned product listings with integer `price_cents`, currency, and status.
- `watchlist_items`: unique `(user_id, product_id)` watch records.

The foundation deliberately stores admin access as `is_admin` instead of a text access-level column. New users default to non-admin access.

## Migrations

```bash
cd apps/api
alembic upgrade head
alembic downgrade base
```

The initial migration creates the foundation tables, foreign keys, unique constraints, timestamp columns, integer money columns, and the PostgreSQL `pgcrypto` extension used by UUID defaults.

## Seed Data

```bash
cd apps/api
python -m app.db.seed
```

Seed data is idempotent by slug and includes representative categories and products from the current static storefront:

- `sneakers`
- `streetwear`
- `collectibles`

Run the seed command more than once to verify duplicate categories or products are not created.

