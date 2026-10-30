from __future__ import annotations

import pytest

from tests.postgres_support import MISSING_POSTGRES_REASON, require_postgres_url, validate_postgres_url


def test_postgres_guard_skips_clearly_when_url_is_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_POSTGRES_DATABASE_URL", raising=False)
    with pytest.raises(pytest.skip.Exception, match=MISSING_POSTGRES_REASON):
        require_postgres_url()


@pytest.mark.parametrize("url", ["sqlite+pysqlite:///:memory:", "mysql+pymysql://localhost/test"])
def test_postgres_guard_rejects_other_dialects_before_connecting(url: str) -> None:
    with pytest.raises(ValueError, match="must use PostgreSQL"):
        validate_postgres_url(url)


def test_postgres_guard_accepts_psycopg_url() -> None:
    url = "postgresql+psycopg://test:test@localhost:5432/test"
    assert validate_postgres_url(url) == url
