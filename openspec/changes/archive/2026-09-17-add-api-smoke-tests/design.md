## Context

The backend already exposes `/health` and versioned `/api/v1` routes for auth, catalog/search, listings, and watchlist. Current tests in `apps/api/tests/test_fastapi_backend.py` exercise these flows with FastAPI's in-process `TestClient` and SQLite fixtures. `apps/api/README.md` documents manual curl checks, but there is no repeatable running-service smoke test that validates the real API server, PostgreSQL-backed seed data, cookies, and HTTP behavior together.

## Goals / Non-Goals

**Goals:**

- Add a reproducible command that smoke tests the running FastAPI API over HTTP.
- Keep the smoke workflow small enough for local pre-integration checks and future CI use.
- Verify public catalog/search, auth session lifecycle, protected listing creation, and watchlist behavior against seeded data.
- Make repeated runs deterministic by using unique test user data and avoiding dependence on manual cleanup.
- Document setup, execution, expected prerequisites, and common failure interpretation.

**Non-Goals:**

- Replace the existing in-process pytest coverage.
- Add new API routes, change response schemas, or alter auth/database behavior.
- Build frontend integration tests or browser tests.
- Add a dedicated end-to-end test environment beyond the existing Docker Compose PostgreSQL setup.
- Test payment, order, bidding, admin, or production image-storage behavior.

## Decisions

### 1. Add a separate smoke-test entrypoint

Create a focused running-service smoke test entrypoint instead of folding this into the existing TestClient test module. The entrypoint can be a pytest-marked integration test module or a small script, but it must run against a configurable base URL and make real HTTP requests.

Rationale: The current unit/integration tests are fast and isolated. A separate entrypoint keeps local `pytest` reliable while letting developers opt into checks that require a running server and PostgreSQL.

Alternatives considered:

- Expand existing `test_fastapi_backend.py`: simple, but would either require a running service for normal tests or mix two different test modes in one file.
- Keep only README curl commands: easy to document, but not repeatable or assertive enough for regressions.

### 2. Use seeded slugs as the catalog fixture boundary

The smoke workflow should assume migrations and seed data have been applied, then discover or assert stable seeded category and product slugs already provided by `app.db.seed`.

Rationale: The backend already has a seed command and docs. Reusing it validates the intended local development path and avoids creating catalog data through private test-only hooks.

Alternatives considered:

- Insert catalog rows directly from the smoke test: faster setup, but bypasses the database seed behavior this workflow is meant to verify.
- Hardcode database IDs: brittle because IDs may differ between local runs.

### 3. Use unique account data for each smoke run

Generate a unique email address for the smoke-test user per run. Use normal public auth endpoints to create sessions and perform protected actions.

Rationale: Unique data avoids duplicate registration conflicts and lets the test run repeatedly against a persistent local database.

Alternatives considered:

- Delete test users before or after each run: more complex and risks requiring privileged cleanup behavior not exposed by the API.
- Reuse one static test account: simpler first run, but repeat runs become order-dependent.

### 4. Keep HTTP client behavior close to frontend usage

Use a real HTTP client that preserves cookies across requests, sends bearer access tokens for protected endpoints, and asserts response status codes plus key response fields.

Rationale: The future Next.js app will depend on both bearer access tokens and HTTP-only refresh cookie behavior. The smoke workflow should validate both at the HTTP boundary.

Alternatives considered:

- Assert only status codes: too weak to catch response-shape regressions.
- Reimplement service-level checks: duplicates existing unit coverage and misses actual HTTP/cookie behavior.

### 5. Report environment failures distinctly

The smoke command should fail clearly when the API base URL is unreachable or seeded data is missing, and the documentation should map those failures to setup commands.

Rationale: Smoke tests are often run during setup. Clear failures keep environment problems from looking like product regressions.

Alternatives considered:

- Let raw connection exceptions or assertion errors surface: lower implementation effort, but rough for local onboarding.

## Risks / Trade-offs

- [Requires running services] The smoke workflow is slower and more stateful than current tests. -> Mitigation: keep it as an explicit command separate from default unit tests.
- [Persistent local data can accumulate] Unique users/listings may remain in local PostgreSQL. -> Mitigation: keep generated data clearly identifiable and avoid conflicts on repeated runs; document optional database reset through existing Alembic commands.
- [Seed assumptions can drift] If seed slugs change, smoke tests may fail even when routes work. -> Mitigation: document the expected seeded records and keep assertions tied to stable slugs maintained by the seed command.
- [Cookie behavior depends on local URL and secure flags] Secure cookies may not round-trip over plain HTTP. -> Mitigation: document local smoke settings and verify `REFRESH_COOKIE_SECURE=false` for local HTTP testing.

## Migration Plan

1. Add the smoke-test entrypoint and any minimal dev dependency wiring needed to run HTTP requests.
2. Cover the public catalog/search, auth session, listing, and watchlist smoke flows using existing API routes.
3. Update backend documentation with the full setup and smoke-test command.
4. Run existing `pytest` plus the new smoke command against a locally migrated and seeded PostgreSQL database.
5. Rollback by removing the smoke-test entrypoint and documentation updates; no database schema rollback is required.
