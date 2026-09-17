from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, status
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

DbSession = Annotated[Session, Depends(get_db)]


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def get_current_user(
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    token = _extract_bearer_token(authorization)
    if token is None:
        raise APIError(status.HTTP_401_UNAUTHORIZED, "not_authenticated", "Authentication is required.")

    user_id = decode_access_token(token)
    if user_id is None:
        raise APIError(status.HTTP_401_UNAUTHORIZED, "invalid_token", "Invalid or expired access token.")

    user = db.get(User, user_id)
    if user is None:
        raise APIError(status.HTTP_401_UNAUTHORIZED, "invalid_token", "Invalid or expired access token.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

