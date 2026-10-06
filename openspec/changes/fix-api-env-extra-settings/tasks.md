## 1. Settings Loader Fix

- [x] 1.1 Update `apps/api/app/core/config.py` so API settings ignore unrelated infrastructure environment variables and verify `Settings()` can be constructed when `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, and `POSTGRES_PORT` are present.
- [x] 1.2 Preserve existing known setting parsing behavior and verify CORS origins, token TTLs, refresh cookie name, and refresh cookie secure flag still parse from environment variables.

## 2. Regression Coverage and Documentation

- [x] 2.1 Extend backend settings tests to include Docker Compose `POSTGRES_*` variables and verify the regression test fails before the fix and passes after the fix.
- [x] 2.2 Update backend setup documentation if needed to clarify that Docker Compose consumes `POSTGRES_*` while FastAPI consumes `DATABASE_URL`, and verify the documented startup path remains accurate.

## 3. Verification

- [x] 3.1 Run `pytest` from `apps/api` and verify the default backend test suite passes.
- [x] 3.2 With `apps/api/.env` containing the copied `.env.example` values, run `alembic upgrade head` and verify settings import no longer fails on extra `POSTGRES_*` values.
- [x] 3.3 With `apps/api/.env` containing the copied `.env.example` values, run `python -m app.db.seed` and verify settings import no longer fails on extra `POSTGRES_*` values.
- [x] 3.4 With `apps/api/.env` containing the copied `.env.example` values, start `uvicorn app.main:app --reload` long enough to verify application import succeeds.
- [x] 3.5 Run `openspec validate fix-api-env-extra-settings --strict` and verify the change remains valid.
