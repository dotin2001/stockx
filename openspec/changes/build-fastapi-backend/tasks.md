## 1. API Structure and Configuration

- [x] 1.1 Add versioned router structure under `apps/api/v1/`, mount it from `app.main` under `/api/v1`, and verify `GET /health` plus one `/api/v1` route can be reached with the test client.
- [x] 1.2 Extend backend settings for token signing, access-token TTL, refresh-token TTL, refresh cookie name, cookie security flags, and CORS origins, and verify settings load from environment variables without committing secrets.
- [x] 1.3 Add shared API error helpers or exception handlers for validation, authentication, conflict, authorization, and not-found responses, and verify representative error tests assert stable JSON response shapes.

## 2. Schemas, Services, and Dependencies

- [x] 2.1 Create Pydantic schema modules for users, auth tokens, categories, products, listings, watchlist items, pagination, and common errors, and verify schema serialization tests cover public response shapes.
- [x] 2.2 Create service modules for auth, catalog/search, listings, and watchlist behavior, and verify service unit tests can exercise database logic without route handlers.
- [x] 2.3 Add backend dependencies for database sessions, current-user resolution, optional current-user resolution if needed, and protected-route authentication, and verify unauthenticated protected requests return authentication errors.

## 3. Authentication API

- [x] 3.1 Add password hashing and verification utilities using a maintained Argon2 or bcrypt-based dependency, and verify tests prove raw passwords are never stored and valid/invalid password checks behave correctly.
- [x] 3.2 Implement `POST /api/v1/auth/register`, and verify successful registration creates a user, returns public user data, returns an access token, and sets an HTTP-only refresh cookie.
- [x] 3.3 Verify registration rejects duplicate email addresses and invalid payloads with consistent conflict or validation errors.
- [x] 3.4 Implement `POST /api/v1/auth/login`, and verify valid credentials return public user data, an access token, and an HTTP-only refresh cookie.
- [x] 3.5 Verify login rejects unknown emails and incorrect passwords without revealing which credential failed.
- [x] 3.6 Implement `GET /api/v1/auth/me`, and verify valid access tokens return the current user while missing/invalid tokens are rejected.
- [x] 3.7 Implement `POST /api/v1/auth/refresh`, and verify refresh rotates the refresh token record, replaces the refresh cookie, returns a new access token, and rejects reuse of the previous refresh token.
- [x] 3.8 Implement `POST /api/v1/auth/logout`, and verify logout revokes the active refresh token, clears the refresh cookie, and prevents the same refresh token from being accepted again.

## 4. Public Catalog and Search API

- [x] 4.1 Implement `GET /api/v1/categories`, and verify seeded categories return stable slugs and display names without authentication.
- [x] 4.2 Implement `GET /api/v1/products` with pagination parameters, and verify product summaries include slug, name, category, image URL, lowest ask cents, and sold count.
- [x] 4.3 Implement `GET /api/v1/categories/{slug}/products`, and verify existing category slugs return only products in that category while missing slugs return not-found errors.
- [x] 4.4 Implement `GET /api/v1/products/{slug}`, and verify existing product slugs return detail data with category and variants while missing slugs return not-found errors.
- [x] 4.5 Implement `GET /api/v1/search?q=...`, and verify non-empty queries return matching product summaries while empty or missing queries return validation errors.

## 5. Protected Marketplace API

- [x] 5.1 Implement `POST /api/v1/listings`, and verify an authenticated user can create an active listing for an existing product with integer price cents and supported currency.
- [x] 5.2 Verify listing creation rejects unauthenticated requests, missing products, invalid variants, and non-positive or non-integer prices.
- [x] 5.3 Implement `GET /api/v1/watchlist`, and verify an authenticated user receives only their own watched products.
- [x] 5.4 Implement `POST /api/v1/watchlist`, and verify adding an existing product creates one watchlist item while duplicate adds are rejected.
- [x] 5.5 Implement `DELETE /api/v1/watchlist/{id}`, and verify users can remove their own watchlist items but cannot delete another user's item.

## 6. Documentation and Verification

- [x] 6.1 Update `apps/api/README.md` and project docs with the final API setup, environment variables, auth cookie behavior, route list, migration/seed commands, and smoke-test commands, and verify the docs match the implemented routes.
- [x] 6.2 Add or update backend tests for health, auth, catalog/search, listings, watchlist, protected-route rejection, and consistent errors, and verify `pytest` passes from `apps/api`.
- [x] 6.3 Run `alembic upgrade head`, seed data, and the backend test suite against local PostgreSQL, and verify the API can read seeded categories/products and complete an auth/listing/watchlist smoke flow.
- [x] 6.4 Run OpenSpec validation for `build-fastapi-backend`, and verify the change remains valid after implementation updates.
