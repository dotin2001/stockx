## 1. Smoke-Test Entrypoint

- [x] 1.1 Choose the smoke-test entrypoint shape under `apps/api` and verify it can accept an API base URL without affecting default `pytest` behavior.
- [x] 1.2 Add any minimal dev dependency or package-script wiring needed for external HTTP requests and verify dependency installation metadata remains valid.
- [x] 1.3 Implement clear connection and prerequisite failure handling for unreachable API services and verify failures explain which setup step is missing.

## 2. Public API Smoke Coverage

- [x] 2.1 Add smoke coverage for `GET /health` and verify it asserts a successful service-ready response from a running API.
- [x] 2.2 Add smoke coverage for `GET /api/v1/categories` and verify seeded category slugs and display names are present.
- [x] 2.3 Add smoke coverage for product list and product detail endpoints and verify seeded product summary/detail fields, category data, and variants are asserted.
- [x] 2.4 Add smoke coverage for `GET /api/v1/search?q=...` and empty search validation, and verify both matching seeded results and stable validation error JSON are asserted.

## 3. Auth and Protected Flow Smoke Coverage

- [x] 3.1 Add unique smoke-test user generation and verify repeated runs do not fail because a previous run created user data.
- [x] 3.2 Add registration smoke coverage and verify public user data, bearer access token, and HTTP-only refresh cookie behavior are asserted.
- [x] 3.3 Add login, current-user, refresh, and logout smoke coverage and verify access-token usage, refresh-cookie rotation, cookie clearing, and rejected session reuse are asserted.
- [x] 3.4 Add unauthenticated listing creation coverage and verify protected endpoints return authentication errors.
- [x] 3.5 Add authenticated listing creation coverage and verify an active listing can be created for a seeded product with positive integer price cents.
- [x] 3.6 Add watchlist add/list/delete and duplicate-add coverage and verify owned item visibility, successful removal, and conflict-style duplicate rejection are asserted.

## 4. Documentation and Verification

- [x] 4.1 Update backend API documentation with PostgreSQL startup, migration, seed, API server, environment variable, and smoke-test command steps, and verify the documented route assumptions match the implemented smoke flow.
- [x] 4.2 Document repeated-run behavior, generated test data, optional local cleanup/reset guidance, and common smoke failure meanings, and verify the notes cover connection failures and missing seeded data.
- [x] 4.3 Run the default backend test suite and verify existing `pytest` coverage still passes without requiring a running API service.
- [x] 4.4 Run the new smoke-test command against local PostgreSQL with migrations and seed data applied, and verify health, catalog/search, auth, listing, and watchlist flows pass end to end.
- [x] 4.5 Run `openspec validate add-api-smoke-tests --strict` and verify the change remains valid after implementation updates.
