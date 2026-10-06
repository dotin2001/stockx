## Why

The FastAPI backend now has authenticated and public marketplace routes, but current verification is mostly in-process pytest coverage plus manual curl examples. A reproducible API smoke-test layer is needed so local development and future frontend integration can quickly prove the running service, PostgreSQL data, auth cookies, protected actions, and error responses work together.

## What Changes

- Add a repeatable API smoke-test workflow for a running FastAPI service backed by the local PostgreSQL database.
- Cover health, catalog, search, registration, login, current-user restore, refresh-token rotation, logout, listing creation, and watchlist operations through real HTTP requests.
- Add setup and teardown guidance so smoke tests can run without depending on manual browser or curl steps.
- Document the command(s), required environment, and expected seeded data assumptions for local API verification.
- Keep existing API routes and response contracts unchanged.

## Capabilities

### New Capabilities

- `api-smoke-testing`: Defines the expected behavior for reproducible running-service API smoke tests across public catalog, auth/session, protected marketplace flows, and stable error responses.

### Modified Capabilities

- None.

## Impact

- Backend tests: adds or extends test tooling for running-service API smoke coverage outside the existing in-process TestClient tests.
- Backend docs: updates `apps/api/README.md` or nearby docs with setup, execution, and troubleshooting notes for API smoke tests.
- Local environment: relies on the existing FastAPI app, PostgreSQL Docker Compose service, Alembic migrations, and seed command.
- API behavior: no intentional route, schema, database, or auth-contract changes.
