# AGENTS.md

Guidance for coding agents working in this repository.

## Project Direction

This project is a StockX-style marketplace storefront currently starting from static HTML/CSS/JS. The planned direction is a full-stack marketplace foundation:

- Frontend: Next.js, TypeScript, Tailwind CSS
- Backend: FastAPI
- Database: PostgreSQL
- Auth: email/password with hashed passwords, short-lived access tokens, and HTTP-only refresh cookies

Start with documentation and project-local skills before implementation. Use OpenSpec artifacts under `openspec/` as the source of truth for planned behavior before implementing large changes.

## Project Skills

Use these project-local skills when the task matches their area:

- `stockx-frontend`: Next.js, TypeScript, Tailwind CSS, frontend routes/components, static-to-frontend migration.
- `stockx-backend`: FastAPI backend, API routes, service boundaries, validation, auth integration.
- `stockx-database`: PostgreSQL schema, SQLAlchemy models, Alembic migrations, seed data.

## Planned Repository Layout

```text
stockx/
  apps/
    web/          Next.js frontend
    api/          FastAPI backend
  packages/
    shared/       Optional shared generated types or utilities
  infra/
    docker/       Local PostgreSQL and service orchestration
  openspec/       Specs, proposals, designs, tasks
```

The existing static files (`index.html`, `streetwear.html`, `collectibles.html`, `css/`, `js/`) should remain until the Next.js app reaches route and content parity.

## Frontend Conventions

- Use Next.js App Router with TypeScript.
- Use Tailwind CSS for styling.
- Build reusable components for repeated UI: header, search bar, category navigation, product cards, grids, auth forms, and empty/error/loading states.
- Keep marketplace pages data-driven. Do not reintroduce hardcoded product lists in page markup.
- Prefer accessible semantic elements for navigation, forms, and product links.
- Keep guest/authenticated navigation states explicit.

Expected routes:

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

## Backend Conventions

- Use FastAPI with Pydantic schemas.
- Keep API routes under a versioned prefix such as `/api/v1`.
- Separate routers, schemas, models, services, and database/session setup.
- Return consistent validation and error responses.
- Protect account, listing, sell, and watchlist operations with auth dependencies.

Expected API areas:

```text
auth
users
categories
products
search
listings
watchlist
```

## Database Conventions

- Use PostgreSQL as the primary datastore.
- Use SQLAlchemy 2.x style models and Alembic migrations.
- Keep migrations reviewable and deterministic.
- Seed representative categories and products from the current static storefront.
- Store refresh token records server-side in a revocable/rotatable form.

Initial entities:

```text
users
refresh_tokens
categories
products
product_variants
listings
watchlist_items
```

## Auth Conventions

- Hash passwords with Argon2 or bcrypt.
- Do not store raw passwords or raw refresh tokens.
- Use short-lived access tokens.
- Store refresh tokens in HTTP-only cookies.
- Rotate refresh tokens on refresh.
- Revoke refresh tokens on logout.
- Never rely only on frontend hiding for protected actions; enforce authorization in the backend.

## Verification Expectations

When implementation exists, prefer these checks before handing work back:

- Frontend lint/type/build checks.
- Backend tests.
- Database migration apply/rollback or at least migration apply against local PostgreSQL.
- Auth smoke test: signup, login, restore current user, logout.
- Marketplace smoke test: browse categories, search, open product detail, access protected account/sell route.

If a command cannot be run because tooling is not installed yet, state that clearly in the final response.

## OpenSpec Workflow

- Use `$openspec-propose` for planning artifacts.
- Use `$openspec-apply-change` before implementation.
- Do not silently implement broad architectural changes without an OpenSpec change.
- Keep `proposal.md`, `design.md`, specs, `tasks.md`, `AGENTS.md`, and `project.md` consistent when scope changes.
