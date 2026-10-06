# StockX-Style Marketplace Project

## Overview

This project is a StockX-style marketplace storefront. It currently exists as static HTML/CSS/JS pages with hardcoded product data, placeholder auth links, and simple DOM interactions. The planned direction is to migrate it into a full-stack marketplace foundation with a typed frontend, backend API, durable database, and authenticated user flows.

## Target Stack

- Frontend: Next.js, TypeScript, Tailwind CSS
- Backend: FastAPI
- Database: PostgreSQL
- ORM and migrations: SQLAlchemy and Alembic
- Auth: email/password, hashed passwords, short-lived access tokens, HTTP-only refresh cookies, refresh-token rotation
- Local development: Docker Compose for PostgreSQL and service coordination

## Product Scope

The foundation should support:

- Home storefront with featured product groups.
- Category browsing for sneakers, streetwear, collectibles, and future categories.
- Product search.
- Product detail pages.
- User registration and login.
- Session restore and logout.
- Account page.
- Authenticated sell/listing entry flow.
- Authenticated watchlist foundation.
- Seeded development catalog based on representative products from the current static pages.
- Simple admin authorization marker stored as `users.is_admin`.

Out of scope for the first foundation:

- Payment processing.
- Real StockX integration.
- Real-time bids or auctions.
- Production image upload/storage.
- OAuth login.
- Full admin dashboard.

## Architecture

```text
Browser
  |
  v
Next.js Web App
  |
  v
FastAPI REST API
  |
  v
PostgreSQL
```

The frontend owns presentation, routing, and user interaction. The backend owns validation, auth, API contracts, and business rules. PostgreSQL owns durable marketplace data.

## Planned Repository Layout

```text
stockx/
  apps/
    web/          Next.js + TypeScript + Tailwind CSS
    api/          FastAPI application
  packages/
    shared/       Optional shared generated types or documentation
  infra/
    docker/       PostgreSQL and local development support
  openspec/       Product and implementation planning
```

Existing static files should stay available until the new app reaches visual and route parity.

## Frontend Plan

Initial routes:

```text
/
/category/[slug]
/product/[slug]
/search
/login
/signup
/account
/sell
```

Core components:

- Header
- SearchBar
- CategoryNav
- ProductCard
- ProductGrid
- ProductDetail
- AuthForm
- AccountSummary
- Empty, loading, and error states

The frontend should fetch catalog and auth state from the backend instead of embedding product records in HTML.

## Backend Plan

Implemented API endpoints:

```text
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/refresh
GET    /api/v1/auth/me

GET    /api/v1/categories
GET    /api/v1/categories/{slug}/products
GET    /api/v1/products
GET    /api/v1/products/{slug}
GET    /api/v1/search?q=...

POST   /api/v1/listings
GET    /api/v1/watchlist
POST   /api/v1/watchlist
DELETE /api/v1/watchlist/{id}
```

Current backend modules:

```text
apps/api/app/api/v1/
apps/api/app/core/
apps/api/app/db/
apps/api/app/models/
apps/api/app/schemas/
apps/api/app/services/
```

Protected account, listing, and watchlist routes require a bearer access token. Refresh tokens are stored in an HTTP-only cookie named `stockx_refresh` by default and are rotated on refresh.

## Database Plan

Initial tables:

```text
users
refresh_tokens
categories
products
product_variants
listings
watchlist_items
```

Important rules:

- Users have unique email addresses.
- Passwords are stored only as hashes.
- Admin access is stored as `is_admin BOOLEAN NOT NULL DEFAULT FALSE`, not as a text role/access-level column.
- Refresh tokens are stored in revocable/rotatable form.
- Categories contain products.
- Products may have variants.
- Authenticated users may create initial listings.
- Users may watch products.

Current database foundation files:

```text
apps/api/app/models/
apps/api/alembic/
apps/api/app/db/seed.py
infra/docker/docker-compose.yml
docs/database.md
```

Foundation commands:

```text
docker compose -f infra/docker/docker-compose.yml --env-file apps/api/.env.example up -d postgres
cd apps/api
alembic upgrade head
python -m app.db.seed
alembic downgrade base
```

## Auth Plan

Auth should start with email/password because it is easier to test and sufficient for the foundation.

Flow:

1. User signs up or logs in.
2. Backend validates credentials.
3. Backend returns current user state and access token information.
4. Backend sets a refresh token in an HTTP-only cookie.
5. Frontend restores user state on app load.
6. Logout revokes the refresh token and returns the UI to guest state.

Backend authorization must be enforced even when the frontend hides protected actions.

Auth implementation notes:

- Passwords are hashed with Argon2.
- Access tokens are signed and short-lived.
- Refresh tokens are stored only as hashes in the database.
- Logout revokes the active refresh token and clears the cookie.

## Roadmap

1. Documentation and conventions.
2. Project-local skills for frontend, backend, and database work.
3. Monorepo folder setup.
4. Next.js frontend scaffold.
5. FastAPI backend scaffold.
6. PostgreSQL, SQLAlchemy, and Alembic setup.
7. Initial schema and seed data.
8. Public catalog/search/product APIs. Done in `build-fastapi-backend`.
9. Auth backend and protected listing/watchlist foundations. Done in `build-fastapi-backend`.
10. Frontend catalog integration.
11. Frontend auth state and protected page integration.
12. Verification, smoke tests, and static file cleanup after parity.

## Project Skills

The first project-local skills are:

```text
.agents/skills/stockx-frontend/SKILL.md
.agents/skills/stockx-backend/SKILL.md
.agents/skills/stockx-database/SKILL.md
```

Use them to keep future frontend, backend, and database work aligned with this plan before writing implementation code.

## Planning Artifacts

Primary OpenSpec change:

```text
openspec/changes/build-fullstack-marketplace-foundation/
```

Review the proposal, design, spec, and tasks there before implementation.
