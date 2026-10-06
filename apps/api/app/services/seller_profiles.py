from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SellerProfile, User
from app.schemas.seller import SellerProfileUpsert


def get_seller_profile(db: Session, *, user: User) -> SellerProfile | None:
    return db.scalar(select(SellerProfile).where(SellerProfile.user_id == user.id))


def is_seller(db: Session, *, user: User) -> bool:
    return get_seller_profile(db, user=user) is not None


def upsert_seller_profile(db: Session, *, user: User, payload: SellerProfileUpsert) -> SellerProfile:
    profile = get_seller_profile(db, user=user)
    data = payload.model_dump()
    if profile is None:
        profile = SellerProfile(user_id=user.id, **data)
        db.add(profile)
    else:
        for key, value in data.items():
            setattr(profile, key, value)
    db.flush()
    return profile
