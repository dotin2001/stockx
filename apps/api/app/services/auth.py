from __future__ import annotations

from datetime import UTC, datetime, timedelta
import secrets
from uuid import UUID

from fastapi import Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.core.config import settings
from app.core.security import create_access_token, hash_password, hash_refresh_token, verify_password
from app.models import RefreshToken, User


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalize_email(email)))


def register_user(db: Session, *, name: str, email: str, password: str) -> User:
    if get_user_by_email(db, email) is not None:
        raise APIError(status.HTTP_409_CONFLICT, "email_exists", "An account already exists for this email.")

    user = User(name=name.strip(), email=normalize_email(email), password_hash=hash_password(password))
    db.add(user)
    db.flush()
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise APIError(status.HTTP_401_UNAUTHORIZED, "invalid_credentials", "Invalid email or password.")
    return user


def create_refresh_token_record(db: Session, user: User) -> tuple[RefreshToken, str]:
    raw_token = secrets.token_urlsafe(48)
    now = datetime.now(UTC)
    record = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_token),
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
        created_at=now,
    )
    db.add(record)
    db.flush()
    return record, raw_token


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/api/v1/auth",
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.refresh_cookie_name, path="/api/v1/auth")


def issue_session(db: Session, response: Response, user: User) -> str:
    _record, refresh_token = create_refresh_token_record(db, user)
    access_token = create_access_token(user.id)
    set_refresh_cookie(response, refresh_token)
    return access_token


def get_active_refresh_token(db: Session, raw_token: str | None) -> RefreshToken:
    if not raw_token:
        raise APIError(status.HTTP_401_UNAUTHORIZED, "not_authenticated", "Refresh token is required.")

    token_hash = hash_refresh_token(raw_token)
    record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    now = datetime.now(UTC)
    expires_at = record.expires_at if record is not None else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)

    if record is None or record.revoked_at is not None or expires_at is None or expires_at <= now:
        raise APIError(status.HTTP_401_UNAUTHORIZED, "invalid_refresh_token", "Invalid or expired refresh token.")
    return record


def rotate_refresh_token(db: Session, response: Response, raw_token: str | None) -> tuple[User, str]:
    current = get_active_refresh_token(db, raw_token)
    user = current.user
    new_record, new_raw_token = create_refresh_token_record(db, user)
    current.revoked_at = datetime.now(UTC)
    current.replaced_by_token_id = new_record.id
    access_token = create_access_token(user.id)
    set_refresh_cookie(response, new_raw_token)
    return user, access_token


def revoke_refresh_token(db: Session, response: Response, raw_token: str | None) -> None:
    if raw_token:
        token_hash = hash_refresh_token(raw_token)
        record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        if record is not None and record.revoked_at is None:
            record.revoked_at = datetime.now(UTC)
    clear_refresh_cookie(response)


def get_user_by_id(db: Session, user_id: UUID) -> User | None:
    return db.get(User, user_id)
