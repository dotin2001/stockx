from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.models import User
from app.services.auth import normalize_email
from app.services.administrative_audit import write_audit


def _user_not_found() -> APIError:
    return APIError(status.HTTP_404_NOT_FOUND, "user_not_found", "User was not found.")


def _search_filter(search: str):
    needle = f"%{search.strip().lower()}%"
    return or_(func.lower(User.email).like(needle), func.lower(User.name).like(needle))


def list_users(db: Session, *, search: str | None, limit: int, offset: int) -> tuple[list[User], int]:
    filters = []
    if search and search.strip():
        filters.append(_search_filter(search))

    total_statement = select(func.count()).select_from(User)
    statement = select(User).order_by(User.created_at.desc(), User.email.asc()).limit(limit).offset(offset)
    if filters:
        total_statement = total_statement.where(*filters)
        statement = statement.where(*filters)

    total = db.scalar(total_statement) or 0
    return list(db.scalars(statement).all()), total


def get_user(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise _user_not_found()
    return user


def promote_user_by_id(db: Session, *, user_id: UUID, actor: User | None = None, request_id: str = "system") -> User:
    user = get_user(db, user_id)
    before = user.is_admin
    user.is_admin = True
    db.flush()
    if actor is not None and before is not True:
        write_audit(
            db,
            actor=actor,
            action="user.admin.promoted",
            target_type="user",
            target_id=user.id,
            request_id=request_id,
            before={"is_admin": before},
            after={"is_admin": True},
        )
    return user


def promote_user_by_email(db: Session, *, email: str, actor: User | None = None, request_id: str = "system") -> User:
    user = db.scalar(select(User).where(User.email == normalize_email(email)))
    if user is None:
        raise _user_not_found()
    return promote_user_by_id(db, user_id=user.id, actor=actor, request_id=request_id)


def demote_user(db: Session, *, user_id: UUID, actor: User, request_id: str = "system") -> User:
    user = get_user(db, user_id)
    if user.id == actor.id:
        raise APIError(
            status.HTTP_409_CONFLICT,
            "self_demotion_rejected",
            "Supreme admins cannot demote their own account.",
        )
    if user.is_supreme_admin:
        raise APIError(
            status.HTTP_409_CONFLICT,
            "supreme_admin_protected",
            "Supreme-admin access cannot be changed through in-app user management.",
        )
    before = user.is_admin
    user.is_admin = False
    db.flush()
    if before is not False:
        write_audit(
            db,
            actor=actor,
            action="user.admin.demoted",
            target_type="user",
            target_id=user.id,
            request_id=request_id,
            before={"is_admin": before},
            after={"is_admin": False},
        )
    return user
