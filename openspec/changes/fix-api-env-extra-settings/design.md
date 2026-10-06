## Context

See `proposal.md` for motivation. The API settings object is created at import time in `app.core.config`, and it reads `apps/api/.env` through Pydantic Settings. The documented setup tells developers to copy `.env.example` to `.env`, while `.env.example` contains both FastAPI application settings and Docker Compose `POSTGRES_*` settings. Pydantic currently rejects those extra keys, so any command importing settings fails before it can run.

## Goals / Non-Goals

**Goals:**

- Let the API settings loader ignore environment keys that are not part of the FastAPI application settings.
- Preserve parsing for known app settings, especially CORS origins and boolean cookie flags.
- Verify the copied `.env.example` workflow works for settings construction, migrations, seed data, and API startup.
- Keep the local Docker Compose command compatible with the existing `.env.example` file.

**Non-Goals:**

- Redesign all local environment management.
- Add a new settings package or external configuration service.
- Change database credentials, Docker Compose service names, or the API route surface.
- Introduce production secret-management behavior.

## Decisions

### 1. Configure API settings to ignore unrelated environment keys

Set the Pydantic Settings model to ignore extra inputs from `.env` rather than failing on keys the API does not consume.

Rationale: This directly fixes the observed traceback while keeping the current documented single-example-env workflow intact. It also matches a common deployment reality: application processes often see environment variables owned by infrastructure, platform, or orchestration layers.

Alternatives considered:

- Remove `POSTGRES_*` from `.env.example`: would make the app load, but would make the same file less useful for Docker Compose and force developers to maintain separate env files immediately.
- Add `postgres_user`, `postgres_password`, `postgres_db`, and `postgres_port` to `Settings`: avoids the error, but implies the FastAPI app uses these fields even though it actually consumes `DATABASE_URL`.
- Split app and Docker env examples now: cleaner long term, but larger than needed for this startup blocker.

### 2. Add focused settings regression coverage

Extend the existing settings test to include Docker Compose `POSTGRES_*` variables and assert known API settings still parse correctly.

Rationale: This catches the exact failure mode without needing to spawn Alembic or Uvicorn in the unit test suite.

Alternatives considered:

- Only rely on manual startup verification: quicker, but this is a small regression that should stay covered.
- Add a separate integration test that copies `.env.example`: more realistic, but more file-system heavy than necessary for the core behavior.

### 3. Keep documentation explicit about variable ownership

Clarify that `POSTGRES_*` values are used by Docker Compose while `DATABASE_URL` is what the FastAPI app uses.

Rationale: The bug came from a legitimate confusion in the setup path. A short note keeps the fix understandable for future local setup.

Alternatives considered:

- Leave docs unchanged after code fix: technically works, but the mixed env file remains surprising.

## Risks / Trade-offs

- [Ignoring extras can hide misspelled app env vars] A typo like `REFRESH_COOKI_SECURE` would be ignored instead of rejected. -> Mitigation: keep tests for expected app setting names and document the supported variables.
- [Single env file remains mixed-purpose] Docker and API settings still live together. -> Mitigation: clarify ownership in docs and defer a split until the local environment grows more complex.
- [Import-time settings still fail for invalid known values] Bad booleans or malformed typed values can still block startup. -> Mitigation: this is desirable for known settings; tests should cover accepted forms.

## Migration Plan

1. Update API settings configuration to ignore extra environment keys.
2. Extend settings tests to include `POSTGRES_*` values from the copied example env path.
3. Update README wording if needed to explain which variables Docker Compose consumes versus which variables FastAPI consumes.
4. Verify `pytest`, `alembic upgrade head`, `python -m app.db.seed`, and `uvicorn app.main:app --reload` no longer fail from settings validation when `.env` includes `POSTGRES_*`.
