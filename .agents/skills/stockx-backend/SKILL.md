---
name: stockx-backend
description: Use when planning, building, reviewing, or refactoring this project's FastAPI backend, API routes, auth integration, and service boundaries.
---

# StockX Backend Skill

Use this skill for work in the planned `apps/api` FastAPI backend.

## Project Context

The project is moving from a static StockX-style storefront to a full-stack marketplace foundation. The backend owns API contracts, validation, authentication, authorization, database access, and business rules.

Target backend stack:

- FastAPI
- Pydantic schemas
- SQLAlchemy
- Alembic
- PostgreSQL

## Backend Shape

Recommended structure:

```text
apps/api/
  app/
    main.py
    core/
      config.py
      security.py
    db/
      session.py
      base.py
    models/
    schemas/
    services/
    api/
      v1/
```

Expected API areas:

- `auth`
- `users`
- `categories`
- `products`
- `search`
- `listings`
- `watchlist`

## API Guidance

- Put public endpoints under a versioned prefix such as `/api/v1`.
- Keep route handlers thin; push business logic into services.
- Use Pydantic request and response schemas for external API boundaries.
- Return consistent validation and error responses.
- Keep public catalog endpoints unauthenticated.
- Protect account, sell, listing, and watchlist operations with backend auth checks.
- Do not rely on frontend hiding as the only authorization layer.

## Auth Guidance

Use email/password auth for the foundation:

- Hash passwords with Argon2 or bcrypt.
- Use short-lived access tokens.
- Store refresh tokens in HTTP-only cookies.
- Store only revocable token records or hashes server-side.
- Rotate refresh tokens on refresh.
- Revoke refresh tokens on logout.

## Verification

When backend tooling exists, verify with the project's documented commands for:

- Unit tests
- API integration tests
- Health endpoint
- Auth flows: signup, login, current user, refresh, logout
- Protected-route rejection for unauthenticated requests

If tooling has not been scaffolded yet, state that verification is blocked by missing backend setup.
