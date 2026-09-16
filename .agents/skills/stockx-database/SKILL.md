---
name: stockx-database
description: Use when planning, building, reviewing, or refactoring this project's PostgreSQL schema, migrations, seed data, and persistence rules.
---

# StockX Database Skill

Use this skill for work on the planned PostgreSQL database, SQLAlchemy models, Alembic migrations, and development seed data.

## Project Context

The current project has no database. Product and category data are hardcoded in static HTML. The target foundation uses PostgreSQL as the durable source for users, auth sessions, categories, products, variants, listings, and watchlists.

## Initial Data Model

Expected initial entities:

```text
users
refresh_tokens
categories
products
product_variants
listings
watchlist_items
```

Useful relationships:

- A category has many products.
- A product belongs to a category.
- A product can have variants.
- A user can create listings.
- A user can watch products.
- Refresh tokens belong to users and can be revoked or rotated.

## Schema Guidance

- Use PostgreSQL-compatible types and constraints.
- Use unique constraints for user email addresses and stable slugs.
- Store money as integer cents or a precise numeric type; do not use floating point for prices.
- Keep timestamps for auditable records.
- Use foreign keys for ownership and catalog relationships.
- Avoid destructive migrations unless explicitly requested and reviewed.
- Keep migrations deterministic and reviewable.

## Seed Data Guidance

- Seed representative categories and products from the current static storefront.
- Keep seed data small enough for local development.
- Prefer stable slugs for seeded categories and products.
- External image URLs are acceptable for the first seed, but mark production image storage as future work.

## Verification

When database tooling exists, verify with the project's documented commands for:

- PostgreSQL container startup
- Migration apply
- Migration rollback when supported
- Seed execution
- API query against seeded products/categories

If tooling has not been scaffolded yet, state that verification is blocked by missing database setup.
