## Why

The project has a PostgreSQL/SQLAlchemy database foundation, but the FastAPI app currently exposes only a health endpoint. A real backend API is needed now so the future Next.js storefront can load catalog data, authenticate users, and perform protected marketplace actions through durable server-side rules.

## What Changes

- Add a versioned FastAPI API surface under `/api/v1`.
- Add email/password authentication with password hashing, short-lived access tokens, HTTP-only refresh cookies, refresh-token rotation, current-user restore, and logout revocation.
- Add public catalog endpoints for categories, product lists, product detail, and search backed by the existing SQLAlchemy models.
- Add protected account, listing creation, and watchlist endpoints enforced by backend auth dependencies.
- Add Pydantic schemas, route modules, services, and consistent API error behavior.
- Add backend tests and smoke checks for health, auth, catalog/search, listing, and watchlist flows.

## Capabilities

### New Capabilities

- `fastapi-backend`: Defines the versioned FastAPI backend behavior for authentication, public catalog/search APIs, protected listing/watchlist/account operations, and API error/verification expectations.

### Modified Capabilities

- None.

## Impact

- Backend: expands `apps/api` from a database foundation plus health endpoint into the first usable API layer.
- Auth: introduces credential hashing, token creation/validation, refresh-cookie lifecycle, and auth dependencies.
- Database: reuses the existing `users`, `refresh_tokens`, `categories`, `products`, `product_variants`, `listings`, and `watchlist_items` tables without changing the initial schema unless implementation reveals a required follow-up change.
- Frontend: enables future Next.js routes to consume real backend data instead of static HTML product markup.
- Dependencies: may add focused auth/test dependencies such as password hashing, JWT/token signing, and API test clients.
