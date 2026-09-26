from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import User
from app.services.auth import get_user_by_email, normalize_email


class AdminPromotionError(Exception):
    pass


def promote_existing_user(db: Session, *, email: str) -> User:
    normalized_email = normalize_email(email)
    user = get_user_by_email(db, normalized_email)
    if user is None:
        raise AdminPromotionError(f"User not found: {normalized_email}")
    user.is_admin = True
    db.flush()
    return user


def grant_supreme_admin(db: Session, *, email: str) -> User:
    normalized_email = normalize_email(email)
    user = get_user_by_email(db, normalized_email)
    if user is None:
        raise AdminPromotionError(f"User not found: {normalized_email}")
    user.is_admin = True
    user.is_supreme_admin = True
    db.flush()
    return user
