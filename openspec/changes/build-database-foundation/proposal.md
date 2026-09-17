## Why

The project needs a durable PostgreSQL database foundation before the backend and frontend can move away from hardcoded static product data. A simple admin marker should be part of the first schema so normal users and admins can be authorized consistently without introducing broader permission machinery too early.

## What Changes

- Add the initial PostgreSQL data model for marketplace catalog and account persistence.
- Define users with an `is_admin` flag that defaults new accounts to non-admin access.
- Add durable tables for users, refresh tokens, categories, products, product variants, listings, and watchlist items.
- Add database constraints for unique user emails, stable slugs, foreign keys, timestamps, and safe price storage.
- Add seed data guidance for representative categories and products from the current static storefront.
- Add migration and verification tasks for applying the schema against a local PostgreSQL database.

## Capabilities

### New Capabilities

- `database-foundation`: Defines the persistent PostgreSQL schema, admin marker, constraints, and seed-data behavior required for the marketplace foundation.

### Modified Capabilities

- None.

## Impact

- Database: introduces the first PostgreSQL schema and migration plan.
- Backend: establishes the data contracts FastAPI models/services will depend on.
- Auth: adds admin marker storage needed for privileged authorization decisions.
- Frontend: enables future catalog pages to load real categories/products instead of hardcoded HTML data.
- Development workflow: requires local PostgreSQL configuration, migration commands, and seed execution.
