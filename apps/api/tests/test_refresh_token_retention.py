from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import tomllib
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.cleanup_refresh_tokens import main as cleanup_main
from app.cleanup_refresh_tokens import parse_args
from app.db.base import Base
from app.models import RefreshToken, User
from app.services.refresh_token_retention import (
    delete_refresh_token_batch,
    preview_refresh_token_cleanup,
    retention_cutoff,
)


NOW = datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
CUTOFF = NOW - timedelta(days=30)
API_ROOT = Path(__file__).resolve().parents[1]


def add_user(db: Session, *, suffix: str = "retention") -> User:
    user = User(
        name="Retention User",
        email=f"{suffix}-{uuid4().hex}@example.test",
        password_hash="unused",
    )
    db.add(user)
    db.flush()
    return user


def add_token(
    db: Session,
    user: User,
    *,
    expires_at: datetime,
    revoked_at: datetime | None = None,
    token_hash: str | None = None,
) -> RefreshToken:
    token = RefreshToken(
        user_id=user.id,
        token_hash=token_hash or f"hash-{uuid4().hex}",
        expires_at=expires_at,
        revoked_at=revoked_at,
        created_at=NOW - timedelta(days=90),
    )
    db.add(token)
    db.flush()
    return token


def remaining_ids(db: Session) -> set:
    db.expire_all()
    return set(db.scalars(select(RefreshToken.id)).all())


def test_cutoff_requires_aware_time_and_is_fixed_to_thirty_days() -> None:
    assert retention_cutoff(now=NOW) == CUTOFF
    with pytest.raises(ValueError, match="timezone-aware"):
        retention_cutoff(now=NOW.replace(tzinfo=None))
    with pytest.raises(ValueError, match="timezone-aware"):
        preview_refresh_token_cleanup(
            object(),  # validation happens before the session is used
            cutoff=CUTOFF.replace(tzinfo=None),
            batch_size=1,
        )


def test_eligibility_is_inclusive_for_expiry_and_revocation(db_session: Session) -> None:
    user = add_user(db_session)
    exact_expiry = add_token(db_session, user, expires_at=CUTOFF)
    exact_revocation = add_token(
        db_session,
        user,
        expires_at=NOW + timedelta(days=1),
        revoked_at=CUTOFF,
    )
    old_expiry = add_token(db_session, user, expires_at=CUTOFF - timedelta(microseconds=1))
    recent_expiry = add_token(db_session, user, expires_at=CUTOFF + timedelta(microseconds=1))
    recent_revocation = add_token(
        db_session,
        user,
        expires_at=NOW + timedelta(days=1),
        revoked_at=CUTOFF + timedelta(microseconds=1),
    )
    active = add_token(db_session, user, expires_at=NOW + timedelta(days=1))
    deleted_ids = {exact_expiry.id, exact_revocation.id, old_expiry.id}
    protected_ids = {recent_expiry.id, recent_revocation.id, active.id}

    result = delete_refresh_token_batch(db_session, cutoff=CUTOFF, batch_size=10)

    assert result.selected_count == 3
    assert result.deleted_count == 3
    assert remaining_ids(db_session) == protected_ids
    assert remaining_ids(db_session).isdisjoint(deleted_ids)


def test_preview_is_bounded_and_does_not_mutate(db_session: Session) -> None:
    user = add_user(db_session)
    tokens = [
        add_token(db_session, user, expires_at=CUTOFF - timedelta(days=index + 1))
        for index in range(4)
    ]
    before = remaining_ids(db_session)

    result = preview_refresh_token_cleanup(db_session, cutoff=CUTOFF, batch_size=2)

    assert result.mode == "dry-run"
    assert result.selected_count == 2
    assert result.deleted_count == 0
    assert remaining_ids(db_session) == before == {token.id for token in tokens}


def test_bounded_deletion_is_deterministic_repeatable_and_idempotent(db_session: Session) -> None:
    user = add_user(db_session)
    oldest = add_token(db_session, user, expires_at=CUTOFF - timedelta(days=3))
    middle = add_token(db_session, user, expires_at=CUTOFF - timedelta(days=2))
    newest = add_token(db_session, user, expires_at=CUTOFF - timedelta(days=1))
    oldest_ids = {oldest.id, middle.id}
    newest_id = newest.id

    first = delete_refresh_token_batch(db_session, cutoff=CUTOFF, batch_size=2)
    assert first.deleted_count == 2
    assert remaining_ids(db_session) == {newest_id}
    assert remaining_ids(db_session).isdisjoint(oldest_ids)

    second = delete_refresh_token_batch(db_session, cutoff=CUTOFF, batch_size=2)
    third = delete_refresh_token_batch(db_session, cutoff=CUTOFF, batch_size=2)
    assert second.deleted_count == 1
    assert third.deleted_count == 0
    assert remaining_ids(db_session) == set()


@pytest.mark.parametrize("batch_size", [0, -1])
def test_service_rejects_non_positive_batch_without_mutation(
    db_session: Session,
    batch_size: int,
) -> None:
    user = add_user(db_session)
    token = add_token(db_session, user, expires_at=CUTOFF)
    with pytest.raises(ValueError, match="positive"):
        delete_refresh_token_batch(db_session, cutoff=CUTOFF, batch_size=batch_size)
    assert remaining_ids(db_session) == {token.id}


def test_replacement_relationships_follow_existing_foreign_key_policy(db_session: Session) -> None:
    user = add_user(db_session)
    protected_replacement = add_token(db_session, user, expires_at=NOW + timedelta(days=1))
    eligible_predecessor = add_token(db_session, user, expires_at=CUTOFF - timedelta(days=2))
    eligible_predecessor.replaced_by_token_id = protected_replacement.id

    eligible_replacement = add_token(db_session, user, expires_at=CUTOFF - timedelta(days=1))
    protected_predecessor = add_token(db_session, user, expires_at=NOW + timedelta(days=2))
    protected_predecessor.replaced_by_token_id = eligible_replacement.id

    protected_chain_tail = add_token(db_session, user, expires_at=NOW + timedelta(days=3))
    protected_replacement.replaced_by_token_id = protected_chain_tail.id
    db_session.flush()

    result = delete_refresh_token_batch(db_session, cutoff=CUTOFF, batch_size=10)
    db_session.flush()
    db_session.expire_all()

    assert result.deleted_count == 2
    assert db_session.get(RefreshToken, protected_replacement.id) is not None
    assert db_session.get(RefreshToken, protected_chain_tail.id) is not None
    incoming = db_session.get(RefreshToken, protected_predecessor.id)
    assert incoming is not None and incoming.replaced_by_token_id is None
    chain = db_session.get(RefreshToken, protected_replacement.id)
    assert chain is not None and chain.replaced_by_token_id == protected_chain_tail.id


def test_cli_preview_delete_zero_and_safe_output(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'retention.sqlite'}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    secret_hash = "never-print-this-token-hash"
    with SessionLocal() as db:
        user = add_user(db, suffix="cli")
        add_token(db, user, expires_at=CUTOFF, token_hash=secret_hash)
        db.commit()

    assert cleanup_main(["--dry-run", "--batch-size", "1"], session_factory=SessionLocal, clock=lambda: NOW) == 0
    preview = capsys.readouterr()
    assert "mode=dry-run" in preview.out and "would_delete=1" in preview.out
    assert secret_hash not in preview.out + preview.err
    with SessionLocal() as db:
        assert db.scalar(select(RefreshToken.id)) is not None

    assert cleanup_main(["--batch-size", "1"], session_factory=SessionLocal, clock=lambda: NOW) == 0
    deleted = capsys.readouterr()
    assert "mode=delete" in deleted.out and "deleted=1" in deleted.out
    assert cleanup_main(["--batch-size", "1"], session_factory=SessionLocal, clock=lambda: NOW) == 0
    zero = capsys.readouterr()
    assert "deleted=0" in zero.out
    engine.dispose()


def test_cli_parsing_and_sanitized_failure(capsys: pytest.CaptureFixture[str]) -> None:
    assert parse_args(["--dry-run", "--batch-size", "7"]).batch_size == 7
    with pytest.raises(SystemExit) as invalid:
        parse_args(["--batch-size", "0"])
    assert invalid.value.code == 2
    capsys.readouterr()

    secret = "sensitive-database-detail"

    def broken_factory():
        raise RuntimeError(secret)

    assert cleanup_main([], session_factory=broken_factory, clock=lambda: NOW) == 1
    output = capsys.readouterr()
    assert "RuntimeError" in output.err
    assert secret not in output.err


def test_console_script_points_to_cleanup_command() -> None:
    metadata = tomllib.loads((API_ROOT / "pyproject.toml").read_text())
    assert (
        metadata["project"]["scripts"]["stockx-api-cleanup-refresh-tokens"]
        == "app.cleanup_refresh_tokens:main"
    )
