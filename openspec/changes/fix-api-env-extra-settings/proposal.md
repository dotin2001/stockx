## Why

Backend startup currently fails after copying `apps/api/.env.example` to `.env` because the FastAPI settings loader rejects Docker Compose variables such as `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, and `POSTGRES_PORT`. This blocks `alembic upgrade head`, seed data, and `uvicorn app.main:app --reload` in the documented local setup path.

## What Changes

- Make the API settings loader tolerate non-application environment variables that may be present in `.env`.
- Preserve strict parsing for known application settings such as `DATABASE_URL`, token/cookie settings, and CORS origins.
- Verify migrations, seed execution, and API startup can load settings when `.env` contains both app config and Docker Compose `POSTGRES_*` values.
- Update or clarify backend setup documentation if needed so local env files are not surprising.

## Capabilities

### New Capabilities

- `api-runtime-config`: Defines the backend runtime configuration behavior needed for local startup, migrations, seed commands, and server boot when environment files include both API settings and infrastructure settings.

### Modified Capabilities

- None.

## Impact

- Backend configuration: updates `apps/api/app/core/config.py` settings behavior.
- Local development: unblocks the documented copy-from-`.env.example` setup path.
- Verification: adds or updates tests around settings loading with extra Docker Compose env keys.
- Documentation: may clarify which env vars are consumed by FastAPI versus Docker Compose.
