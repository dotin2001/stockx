## Context

The repository now has an `apps/api` FastAPI package with a health endpoint, SQLAlchemy models, Alembic migration, seed data, and PostgreSQL local setup. It does not yet have versioned routers, Pydantic API schemas, services, authentication utilities, or endpoint tests for the marketplace flows described in `project.md`.

## Goals / Non-Goals

**Goals:**

- Build the first usable backend API surface under `/api/v1`.
- Keep route handlers thin and move database/business logic into services.
- Implement email/password auth with hashed passwords, access tokens, HTTP-only refresh cookies, refresh-token rotation, and logout revocation.
- Expose public category, product, and search APIs over the existing database foundation.
- Enforce backend authentication for account, listing, and watchlist operations.
- Add focused backend tests and smoke checks that can run locally.

**Non-Goals:**

- Build the Next.js frontend or replace the existing static pages.
- Add payments, bids, orders, checkout, production image upload, OAuth, or a full admin dashboard.
- Change the initial database schema unless implementation reveals a concrete incompatibility that requires a separate OpenSpec update.
- Add fine-grained permissions beyond the existing `users.is_admin` marker.

## Decisions

### 1. Keep one versioned API package

Add route modules under `apps/api/app/api/v1/` and mount them from `app.main` under `/api/v1`.

Rationale: `project.md` and `AGENTS.md` both call for a versioned prefix. A single v1 package keeps the first API small while leaving room for future compatibility-preserving versions.

Alternatives considered:

- Put all routes in `main.py`: fast initially, but would become hard to review as auth, catalog, listings, and watchlist grow.
- Create multiple FastAPI applications: unnecessary for this monorepo foundation.

### 2. Use schemas and services as explicit boundaries

Add Pydantic schemas under `app/schemas/` and service modules under `app/services/`. Routers validate inputs, call services, and translate service outcomes into API responses.

Rationale: The backend conventions require route handlers to stay thin. Schemas keep the external API stable; services keep reusable database logic outside route modules.

Alternatives considered:

- Put database queries directly in routers: fewer files, but makes auth and business rules harder to test and reuse.
- Add a repository layer immediately: potentially useful later, but heavier than needed for the first backend API.

### 3. Use access tokens plus refresh-cookie session records

Use signed short-lived access tokens for API authentication and HTTP-only refresh cookies backed by hashed `refresh_tokens` database records. Refresh rotates tokens by revoking/replacing the previous record. Logout revokes the active refresh record and clears the cookie.

Rationale: This matches the project auth plan and avoids storing raw refresh tokens. The existing `refresh_tokens` table already supports ownership, expiration, revocation, and replacement linkage.

Alternatives considered:

- Server-only sessions without access tokens: simpler token handling, but less aligned with the documented access-token plan.
- Long-lived bearer tokens only: easier to implement but worse revocation behavior and cookie security.

### 4. Hash passwords with a dedicated password hashing dependency

Add a password hashing utility in `app/core/security.py` using Argon2 or bcrypt through a maintained library. Store only `password_hash` in the database.

Rationale: Password hashing is security-sensitive and should not be hand-rolled. The schema already requires hashes, not raw passwords.

Alternatives considered:

- Plain SHA hashing: rejected because it is inappropriate for password storage.
- Database-side hashing: keeps logic out of Python but complicates testing and portability.

### 5. Keep catalog endpoints read-only and unauthenticated

Expose categories, category products, product listings, product detail, and search as public endpoints. Use pagination for list/search responses and stable slugs for lookups.

Rationale: Public browsing is the first marketplace workflow the frontend needs, and the seed data already provides category/product content.

Alternatives considered:

- Require authentication for all catalog APIs: unnecessary friction for storefront browsing.
- Return all products without pagination: okay for seed data but unsafe as the catalog grows.

### 6. Enforce ownership and protected actions in backend dependencies

Use an auth dependency to resolve the current user for protected endpoints. Listing creation uses the authenticated user as owner. Watchlist list/add/remove only operates on items owned by the authenticated user.

Rationale: `AGENTS.md` explicitly says not to rely on frontend hiding for protected behavior.

Alternatives considered:

- Trust user IDs supplied by clients: rejected because clients could spoof ownership.
- Add admin-only management now: out of scope for the first backend API.

### 7. Keep error responses consistent but small

Use FastAPI/Pydantic validation for request shape and add helper behavior for common conflict, not-found, authentication, and authorization errors. Return JSON errors with stable detail suitable for frontend display.

Rationale: The frontend needs predictable errors, but the first API does not need a large error framework.

Alternatives considered:

- Use raw exception messages everywhere: leaks implementation details and creates inconsistent frontend handling.
- Build a full error-code registry now: too heavy before more API domains exist.

## Risks / Trade-offs

- [Token security details are easy to miss] Refresh-token rotation, cookie flags, and raw token storage need careful implementation. -> Mitigation: add auth service tests for login, refresh rotation, logout revocation, and cookie clearing.
- [Search quality will be basic] Initial SQL search over product fields will not match a dedicated search engine. -> Mitigation: keep the endpoint contract simple and improve ranking/indexing later without breaking clients.
- [No schema changes planned] Existing tables may lack convenience columns for richer listing/watchlist responses. -> Mitigation: compose response data through relationships first; propose a database change only if a missing field blocks required behavior.
- [Dependency drift] Adding auth libraries can affect packaging and local setup. -> Mitigation: update `pyproject.toml`, `README.md`, and tests in the same implementation change.

## Migration Plan

1. Add backend API modules, schemas, services, and security utilities without changing existing static frontend files.
2. Reuse the existing database migration; ensure `alembic upgrade head` remains valid.
3. Add or update tests for health, auth, catalog/search, listing, watchlist, and protected-route rejection.
4. Update API documentation with setup, environment variables, auth cookie behavior, and smoke-test commands.
5. Rollback by removing the new API modules and dependencies; no data-destructive rollback should be needed unless a separate schema change is introduced.
