## 1. Database Tooling Setup

- [x] 1.1 Add or confirm the backend database workspace location for SQLAlchemy and Alembic, and verify the expected database files/directories are present.
- [x] 1.2 Add PostgreSQL local development configuration, and verify a local PostgreSQL instance can start and accept connections.
- [x] 1.3 Add database environment variable examples for connection URL and migration settings, and verify no secret values are committed.

## 2. Schema Models

- [x] 2.1 Define the `users` model with UUID primary key, unique email, password hash, `is_admin` boolean defaulting to false, and timestamps, and verify admin access is stored only as a boolean value.
- [x] 2.2 Define the `refresh_tokens` model with user ownership, token hash, expiration, revocation, replacement link, and created timestamp, and verify refresh tokens require an existing user.
- [x] 2.3 Define the `categories` model with unique slug and timestamps, and verify duplicate category slugs are rejected.
- [x] 2.4 Define the `products` model with category ownership, unique slug, display fields, image URL, lowest ask cents, sold count, and timestamps, and verify products require an existing category.
- [x] 2.5 Define the `product_variants` model with product ownership and optional size/color/SKU attributes, and verify variants require an existing product.
- [x] 2.6 Define the `listings` model with user ownership, product ownership, optional variant link, integer price cents, currency, status, and timestamps, and verify listings require existing user and product records.
- [x] 2.7 Define the `watchlist_items` model with user/product ownership and a unique `(user_id, product_id)` constraint, and verify duplicate watchlist entries are rejected.

## 3. Migrations

- [x] 3.1 Create the initial Alembic migration for all database foundation tables and constraints, and verify the migration file contains users, refresh tokens, categories, products, product variants, listings, and watchlist items.
- [x] 3.2 Apply the migration against local PostgreSQL, and verify all expected tables and constraints exist.
- [x] 3.3 Run the migration downgrade in a safe local database, and verify the foundation tables are removed only through the migration path.

## 4. Seed Data

- [x] 4.1 Create idempotent seed data for representative categories including sneakers, streetwear, and collectibles, and verify re-running the seed does not duplicate categories.
- [x] 4.2 Create idempotent seed data for representative products from the current static storefront, and verify products include slugs, category links, image URLs, lowest ask cents, and sold counts when available.
- [x] 4.3 Add seed execution documentation or command wiring, and verify a fresh local database can be migrated and seeded from documented commands.

## 5. Admin Flag and Constraint Verification

- [x] 5.1 Verify new user records default to `is_admin = false` when admin access is not explicitly provided.
- [x] 5.2 Verify `is_admin = true` can be persisted for an authorized seed or administrative path.
- [x] 5.3 Verify admin access is represented by a non-null boolean column and no text access-level column is introduced.
- [x] 5.4 Verify price fields use integer cents and no floating-point price columns are introduced.

## 6. Documentation

- [x] 6.1 Update database documentation in `project.md` or create the new database docs with the final schema summary, admin flag behavior, migration command, and seed command, and verify it matches the implemented migration.
- [x] 6.2 Update `AGENTS.md` if implementation commands or database conventions change, and verify future agents can find the database verification steps.
