from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import secrets
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

from app.core.config import settings

ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "access"

password_hasher = PasswordHasher()


def _jwt_signing_key() -> bytes:
    # The production validator still requires a strong operator-provided secret.
    # A fixed-width derivation also keeps local placeholders out of JWT library
    # weak-key warning paths without changing the configured secret contract.
    return hashlib.sha256(settings.secret_key.get_secret_value().encode("utf-8")).digest()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False


def create_access_token(user_id: UUID) -> str:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "jti": secrets.token_urlsafe(16),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, _jwt_signing_key(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> UUID | None:
    try:
        payload = jwt.decode(token, _jwt_signing_key(), algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        return None

    try:
        return UUID(str(payload["sub"]))
    except (KeyError, ValueError, TypeError):
        return None


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
