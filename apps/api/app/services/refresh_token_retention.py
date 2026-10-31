from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import case, delete, select
from sqlalchemy.orm import Session

from app.models import RefreshToken


RETENTION_DAYS = 30
DEFAULT_BATCH_SIZE = 100


@dataclass(frozen=True)
class RefreshTokenRetentionResult:
    mode: Literal["dry-run", "delete"]
    cutoff: datetime
    batch_size: int
    selected_count: int
    deleted_count: int


def retention_cutoff(*, now: datetime | None = None) -> datetime:
    captured_now = datetime.now(UTC) if now is None else now
    if captured_now.tzinfo is None:
        raise ValueError("retention time must be timezone-aware")
    return captured_now.astimezone(UTC) - timedelta(days=RETENTION_DAYS)


def _validate_batch_size(batch_size: int) -> None:
    if batch_size < 1:
        raise ValueError("batch_size must be positive")


def _utc_cutoff(cutoff: datetime) -> datetime:
    if cutoff.tzinfo is None:
        raise ValueError("cutoff must be timezone-aware")
    return cutoff.astimezone(UTC)


def _eligible_ids_statement(*, cutoff: datetime, batch_size: int, lock_rows: bool):
    # Order by the timestamp that first made a row eligible, then its UUID. The
    # CASE expression behaves consistently on SQLite and PostgreSQL when
    # revoked_at is NULL.
    eligible_at = case(
        (RefreshToken.revoked_at.is_(None), RefreshToken.expires_at),
        (RefreshToken.expires_at <= RefreshToken.revoked_at, RefreshToken.expires_at),
        else_=RefreshToken.revoked_at,
    )
    statement = (
        select(RefreshToken.id)
        .where(
            (RefreshToken.expires_at <= cutoff)
            | (RefreshToken.revoked_at.is_not(None) & (RefreshToken.revoked_at <= cutoff))
        )
        .order_by(eligible_at, RefreshToken.id)
        .limit(batch_size)
    )
    if lock_rows:
        statement = statement.with_for_update(skip_locked=True)
    return statement


def preview_refresh_token_cleanup(
    db: Session,
    *,
    cutoff: datetime,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> RefreshTokenRetentionResult:
    _validate_batch_size(batch_size)
    cutoff = _utc_cutoff(cutoff)
    token_ids = db.scalars(
        _eligible_ids_statement(cutoff=cutoff, batch_size=batch_size, lock_rows=False)
    ).all()
    return RefreshTokenRetentionResult(
        mode="dry-run",
        cutoff=cutoff,
        batch_size=batch_size,
        selected_count=len(token_ids),
        deleted_count=0,
    )


def delete_refresh_token_batch(
    db: Session,
    *,
    cutoff: datetime,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> RefreshTokenRetentionResult:
    _validate_batch_size(batch_size)
    cutoff = _utc_cutoff(cutoff)
    token_ids = db.scalars(
        _eligible_ids_statement(cutoff=cutoff, batch_size=batch_size, lock_rows=True)
    ).all()
    deleted_count = 0
    if token_ids:
        outcome = db.execute(
            delete(RefreshToken)
            .where(RefreshToken.id.in_(token_ids))
            .execution_options(synchronize_session=False)
        )
        deleted_count = outcome.rowcount or 0
    return RefreshTokenRetentionResult(
        mode="delete",
        cutoff=cutoff,
        batch_size=batch_size,
        selected_count=len(token_ids),
        deleted_count=deleted_count,
    )
