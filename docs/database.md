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

- `users`: account identity, unique email, password hash, `is_admin BOOLEAN NOT NULL DEFAULT FALSE`, `is_supreme_admin BOOLEAN NOT NULL DEFAULT FALSE`, timestamps.
- `refresh_tokens`: hashed refresh tokens with expiration, revocation, and replacement linkage.
- `categories`: unique category slugs.
- `products`: required category ownership, unique product slugs, display fields, image URL, integer `lowest_ask_cents`, and sold count.
- `product_variants`: optional size, color, and SKU per product.
- `listings`: user-owned product listings with integer `price_cents`, non-negative `available_quantity`, currency, and status.
- `watchlist_items`: unique `(user_id, product_id)` watch records.

The foundation deliberately stores admin access as boolean flags instead of a text access-level column. New users default to customer access with both flags false. Normal admins use `is_admin`; supreme admins are operator-granted users with both `is_admin` and `is_supreme_admin` true.

Listing quantity represents sellable inventory for a product or variant. Active
listings with `available_quantity > 0` can be used by public cart flows; zero
quantity, sold listings, cancelled listings, and archived products are reported
as unavailable or quantity-limited instead of being silently removed from carts.
Only supreme admins may adjust listing quantity or change inventory status.

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

The catalog contains five configured products in each category. Catalog-only
seeding remains available immediately after migrations and does not create a
user account or login credential.

To add deterministic sellable inventory, first register a user through the API
or web app and promote that existing user to admin. Then run:

```bash
cd apps/api
python -m app.admin promote admin@example.com
python -m app.db.seed --inventory-owner-email admin@example.com
```

The inventory seed creates one category-appropriate purchase option and one
active USD listing per seeded product with quantity `10`. It is idempotent for
the selected admin and reserved `SEED-...` SKUs. Running it again resets those
managed demo listings to their configured price, active status, and quantity
without changing unrelated administrator-created inventory.
