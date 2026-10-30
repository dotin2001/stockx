from __future__ import annotations

import os

import pytest
from sqlalchemy import Engine, create_engine, make_url


POSTGRES_ENV_VAR = "TEST_POSTGRES_DATABASE_URL"
MISSING_POSTGRES_REASON = f"{POSTGRES_ENV_VAR} is not configured"


def validate_postgres_url(raw_url: str) -> str:
    try:
        url = make_url(raw_url)
    except Exception as exc:
        raise ValueError(f"{POSTGRES_ENV_VAR} is not a valid SQLAlchemy database URL") from exc
    if url.get_backend_name() != "postgresql":
        raise ValueError(f"{POSTGRES_ENV_VAR} must use PostgreSQL, not {url.get_backend_name()}")
    return raw_url


def require_postgres_url() -> str:
    raw_url = os.getenv(POSTGRES_ENV_VAR)
    if not raw_url:
        pytest.skip(MISSING_POSTGRES_REASON)
    return validate_postgres_url(raw_url)


def create_postgres_test_engine() -> Engine:
    return create_engine(require_postgres_url(), pool_pre_ping=True)
