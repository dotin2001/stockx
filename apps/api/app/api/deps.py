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


def get_current_admin_user(current_user: CurrentUser) -> User:
    if not (current_user.is_admin or current_user.is_supreme_admin):
        raise APIError(status.HTTP_403_FORBIDDEN, "admin_required", "Admin access is required.")
    return current_user


CurrentAdminUser = Annotated[User, Depends(get_current_admin_user)]


def get_current_supreme_admin_user(current_user: CurrentUser) -> User:
    if not current_user.is_supreme_admin:
        raise APIError(
            status.HTTP_403_FORBIDDEN,
            "supreme_admin_required",
            "Supreme admin access is required.",
        )
    return current_user


CurrentSupremeAdminUser = Annotated[User, Depends(get_current_supreme_admin_user)]
