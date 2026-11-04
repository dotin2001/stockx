from __future__ import annotations

from datetime import UTC, datetime, timedelta
import logging
import secrets
from uuid import UUID, uuid4

from fastapi import Response, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.core.config import settings
from app.core.identity import normalize_email
from app.core.security import create_access_token, hash_password, hash_refresh_token, verify_password
from app.models import AccountChallenge, RefreshToken, User
from app.services.action_delivery import ActionDeliveryError, action_delivery
from app.services.integrity import matches_integrity_target


logger = logging.getLogger("stockx.auth")
EMAIL_UNIQUENESS_TARGETS = ("uq_users_email_normalized", "uq_users_email", "users.email")
VERIFICATION_PURPOSE = "email_verification"
RESET_PURPOSE = "password_reset"


def _email_conflict() -> APIError:
    return APIError(status.HTTP_409_CONFLICT, "email_exists", "An account already exists for this email.")


def _invalid_action_token() -> APIError:
    return APIError(status.HTTP_400_BAD_REQUEST, "invalid_action_token", "The action token is invalid or expired.")


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalize_email(email)))


def register_user(db: Session, *, name: str, email: str, password: str) -> User:
    normalized_email = normalize_email(email)
    if get_user_by_email(db, normalized_email) is not None:
        raise _email_conflict()
    user = User(name=name.strip(), email=normalized_email, password_hash=hash_password(password))
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if matches_integrity_target(exc, EMAIL_UNIQUENESS_TARGETS):
            raise _email_conflict() from exc
        raise
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        raise APIError(status.HTTP_401_UNAUTHORIZED, "invalid_credentials", "Invalid email or password.")
    return user


def create_refresh_token_record(
    db: Session,
    user: User,
    *,
    family_id: UUID | None = None,
) -> tuple[RefreshToken, str]:
    raw_token = secrets.token_urlsafe(48)
    now = datetime.now(UTC)
    record = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_token),
        family_id=family_id or uuid4(),
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
        httponly=settings.refresh_cookie_httponly,
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


def _locked_refresh_token(db: Session, raw_token: str | None) -> RefreshToken:
    if not raw_token:
        raise APIError(
            status.HTTP_401_UNAUTHORIZED,
            "not_authenticated",
            "Refresh token is required.",
            clear_refresh_cookie=True,
        )
    return db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(raw_token))
        .with_for_update()
    )


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def get_active_refresh_token(db: Session, raw_token: str | None) -> RefreshToken:
    record = _locked_refresh_token(db, raw_token)
    expires_at = _aware(record.expires_at) if record is not None else None
    if record is None or record.revoked_at is not None or expires_at is None or expires_at <= datetime.now(UTC):
        raise APIError(
            status.HTTP_401_UNAUTHORIZED,
            "invalid_refresh_token",
            "Invalid or expired refresh token.",
            clear_refresh_cookie=True,
        )
    return record


def rotate_refresh_token(db: Session, response: Response, raw_token: str | None) -> tuple[User, str]:
    current = _locked_refresh_token(db, raw_token)
    now = datetime.now(UTC)
    if current is None:
        raise APIError(
            status.HTTP_401_UNAUTHORIZED,
            "invalid_refresh_token",
            "Invalid or expired refresh token.",
            clear_refresh_cookie=True,
        )

    if current.replaced_by_token_id is not None:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == current.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.commit()
        raise APIError(
            status.HTTP_401_UNAUTHORIZED,
            "invalid_refresh_token",
            "Invalid or expired refresh token.",
            clear_refresh_cookie=True,
        )

    expires_at = _aware(current.expires_at)
    if current.revoked_at is not None or expires_at is None or expires_at <= now:
        raise APIError(
            status.HTTP_401_UNAUTHORIZED,
            "invalid_refresh_token",
            "Invalid or expired refresh token.",
            clear_refresh_cookie=True,
        )

    user = current.user
    new_record, new_raw_token = create_refresh_token_record(db, user, family_id=current.family_id)
    current.revoked_at = now
    current.replaced_by_token_id = new_record.id
    db.flush()
    set_refresh_cookie(response, new_raw_token)
    return user, create_access_token(user.id)


def revoke_refresh_token(db: Session, response: Response, raw_token: str | None) -> None:
    if raw_token:
        record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token)))
        if record is not None and record.revoked_at is None:
            record.revoked_at = datetime.now(UTC)
    clear_refresh_cookie(response)


def revoke_all_refresh_tokens(db: Session, response: Response, user: User) -> int:
    result = db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    clear_refresh_cookie(response)
    return result.rowcount or 0


def _issue_challenge(db: Session, user: User, *, purpose: str, lifetime_minutes: int) -> None:
    raw_token = secrets.token_urlsafe(48)
    now = datetime.now(UTC)
    db.add(
        AccountChallenge(
            user_id=user.id,
            purpose=purpose,
            token_hash=hash_refresh_token(raw_token),
            created_at=now,
            expires_at=now + timedelta(minutes=lifetime_minutes),
        )
    )
    db.commit()
    try:
        action_delivery.send(purpose=purpose, email=user.email, token=raw_token)
    except ActionDeliveryError:
        logger.error(
            "action_delivery_failed",
            extra={"event": "action_delivery_failed", "purpose": purpose, "user_id": str(user.id)},
        )


def request_email_verification(db: Session, *, email: str) -> None:
    user = get_user_by_email(db, email)
    if user is not None and user.verified_at is None:
        _issue_challenge(
            db,
            user,
            purpose=VERIFICATION_PURPOSE,
            lifetime_minutes=settings.verification_token_expire_minutes,
        )


def request_password_reset(db: Session, *, email: str) -> None:
    user = get_user_by_email(db, email)
    if user is not None:
        _issue_challenge(
            db,
            user,
            purpose=RESET_PURPOSE,
            lifetime_minutes=settings.password_reset_token_expire_minutes,
        )


def _consume_challenge(db: Session, *, raw_token: str, purpose: str) -> AccountChallenge:
    challenge = db.scalar(
        select(AccountChallenge)
        .where(
            AccountChallenge.token_hash == hash_refresh_token(raw_token),
            AccountChallenge.purpose == purpose,
        )
        .with_for_update()
    )
    now = datetime.now(UTC)
    expires_at = _aware(challenge.expires_at) if challenge is not None else None
    if challenge is None or challenge.consumed_at is not None or expires_at is None or expires_at <= now:
        raise _invalid_action_token()
    challenge.consumed_at = now
    return challenge


def verify_email(db: Session, *, raw_token: str) -> User:
    challenge = _consume_challenge(db, raw_token=raw_token, purpose=VERIFICATION_PURPOSE)
    user = challenge.user
    if user.verified_at is None:
        user.verified_at = datetime.now(UTC)
    db.flush()
    return user


def reset_password(db: Session, response: Response, *, raw_token: str, new_password: str) -> User:
    challenge = _consume_challenge(db, raw_token=raw_token, purpose=RESET_PURPOSE)
    user = challenge.user
    user.password_hash = hash_password(new_password)
    revoke_all_refresh_tokens(db, response, user)
    db.flush()
    return user


def get_user_by_id(db: Session, user_id: UUID) -> User | None:
    return db.get(User, user_id)
