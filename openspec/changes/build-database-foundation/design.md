## Context

The repository currently has no backend database schema. Catalog data lives in static HTML pages, and project docs identify PostgreSQL, SQLAlchemy, and Alembic as the planned persistence stack. This design covers only the first database foundation, not API implementation or frontend integration.

## Goals / Non-Goals

**Goals:**

- Define the initial PostgreSQL schema for users, admin access, sessions, catalog, listings, and watchlists.
- Store privileged account access with a boolean `is_admin` flag.
- Support local development migrations and seed data.
- Make the schema safe for later FastAPI auth, catalog, and marketplace APIs.

**Non-Goals:**

- Implement FastAPI routes or frontend pages.
- Implement a complete admin dashboard.
- Implement payment, checkout, bids, asks, or order settlement.
- Implement production image upload/storage.
- Build fine-grained account groups or permissions beyond the initial admin flag.

## Decisions

### 1. Use PostgreSQL with SQLAlchemy and Alembic

Use PostgreSQL as the database, SQLAlchemy models as the application data mapping, and Alembic migrations for schema changes.

Rationale: The project needs relational integrity across users, categories, products, listings, and watchlists. Alembic gives the backend an auditable migration path.

Alternatives considered:

- SQLite: simpler locally, but weaker production parity and less useful for marketplace-style relational constraints.
- NoSQL document storage: flexible, but unnecessary for the relational data shape.

### 2. Store admin access directly on `users`

Add a required `is_admin` column to `users`. New application-created users default to non-admin access.

Recommended representation:

```text
users.is_admin BOOLEAN NOT NULL DEFAULT FALSE
```

Rationale: The project currently needs only a simple distinction between normal users and admins. A direct boolean flag is easy to query, enforce, seed, and reason about before any broader permission model exists.

Alternatives considered:

- Separate permission mapping tables: more flexible for many access types, but too heavy before admin functionality exists.
- Text/enum-style access level: more expressive if `seller` or `moderator` concepts appear later, but unnecessary for the current admin/non-admin requirement.

### 3. Use UUID primary keys

Use UUID primary keys for core tables.

Rationale: UUIDs are safe to expose in APIs when needed, avoid sequential ID guessing, and work well across services.

Alternatives considered:

- Integer IDs: simpler and compact, but less suitable for public-facing API identifiers.

### 4. Use integer cents for money

Store prices in integer cents with a currency code where needed.

Example:

```text
lowest_ask_cents INTEGER
price_cents INTEGER NOT NULL
currency TEXT NOT NULL DEFAULT 'USD'
```

Rationale: Integer cents avoid floating-point precision problems and are simple for the first marketplace foundation.

Alternatives considered:

- PostgreSQL `NUMERIC`: precise and flexible, but integer cents are simpler for USD-style prices.
- Floating point: rejected because it can lose precision.

### 5. Keep catalog tables small but extensible

Initial table shape:

```text
users
- id UUID PK
- name TEXT NOT NULL
- email TEXT NOT NULL UNIQUE
- password_hash TEXT NOT NULL
- is_admin BOOLEAN NOT NULL DEFAULT FALSE
- created_at TIMESTAMPTZ NOT NULL
- updated_at TIMESTAMPTZ NOT NULL

refresh_tokens
- id UUID PK
- user_id UUID NOT NULL FK users.id
- token_hash TEXT NOT NULL UNIQUE
- expires_at TIMESTAMPTZ NOT NULL
- revoked_at TIMESTAMPTZ NULL
- replaced_by_token_id UUID NULL FK refresh_tokens.id
- created_at TIMESTAMPTZ NOT NULL

categories
- id UUID PK
- name TEXT NOT NULL
- slug TEXT NOT NULL UNIQUE
- description TEXT NULL
- created_at TIMESTAMPTZ NOT NULL
- updated_at TIMESTAMPTZ NOT NULL

products
- id UUID PK
- category_id UUID NOT NULL FK categories.id
- name TEXT NOT NULL
- slug TEXT NOT NULL UNIQUE
- brand TEXT NULL
- description TEXT NULL
- image_url TEXT NULL
- lowest_ask_cents INTEGER NULL
- total_sold INTEGER NOT NULL DEFAULT 0
- created_at TIMESTAMPTZ NOT NULL
- updated_at TIMESTAMPTZ NOT NULL

product_variants
- id UUID PK
- product_id UUID NOT NULL FK products.id
- size TEXT NULL
- color TEXT NULL
- sku TEXT NULL
- created_at TIMESTAMPTZ NOT NULL
- updated_at TIMESTAMPTZ NOT NULL

listings
- id UUID PK
- user_id UUID NOT NULL FK users.id
- product_id UUID NOT NULL FK products.id
- product_variant_id UUID NULL FK product_variants.id
- price_cents INTEGER NOT NULL
- currency TEXT NOT NULL DEFAULT 'USD'
- status TEXT NOT NULL DEFAULT 'active'
- created_at TIMESTAMPTZ NOT NULL
- updated_at TIMESTAMPTZ NOT NULL

watchlist_items
- id UUID PK
- user_id UUID NOT NULL FK users.id
- product_id UUID NOT NULL FK products.id
- created_at TIMESTAMPTZ NOT NULL
- UNIQUE (user_id, product_id)
```

Rationale: This supports the first catalog and account flows without modeling complete bidding/order/payment systems too early.

### 6. Seed representative static storefront data

Seed a small representative subset from the current static pages:

- Categories: sneakers, streetwear, collectibles
- Several products per category
- Stable slugs
- Existing external image URLs when useful
- Lowest ask and sold count when available

Seed data should be idempotent by slug so it can be re-run safely.

Rationale: Frontend/backend work needs realistic data immediately, and the project already has useful sample content embedded in HTML.

## Risks / Trade-offs

- [Authorization model may grow] A boolean admin flag might not be enough if seller, moderator, or fine-grained permission concepts appear later. -> Mitigation: keep `is_admin` scoped to current admin access and add a richer permission model in a later change if product requirements need it.
- [External image URLs can break] Seeded product images may disappear or change. -> Mitigation: treat them as development seed values and defer production storage.
- [Listing model is intentionally minimal] It does not cover bidding, order settlement, or inventory verification. -> Mitigation: keep listing status extensible and add transaction tables in a later change.
- [UUIDs are less compact] UUID indexes are larger than integer indexes. -> Mitigation: this trade-off is acceptable for public-facing IDs and early marketplace scale.
- [Seed idempotency can be missed] Re-running seeds can duplicate records if slugs are not used consistently. -> Mitigation: require unique slugs and upsert-style seed behavior.

## Migration Plan

1. Add PostgreSQL local development configuration.
2. Add SQLAlchemy and Alembic setup under the backend project when the backend scaffold exists.
3. Create an initial migration for all foundation tables and constraints.
4. Add seed data for representative categories and products.
5. Verify migration apply against local PostgreSQL.
6. Verify seed execution is idempotent.
7. Verify new users default to `is_admin = false` and authorized admin records can store `is_admin = true`.

Rollback strategy:

- Before production data exists, rollback can drop the foundation tables through Alembic downgrade.
- After meaningful data exists, destructive rollback requires explicit backup and approval before dropping tables.
