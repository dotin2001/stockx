from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.api.errors import APIError
from app.schemas.seller import SellerProfileRead, SellerProfileUpsert
from app.services import seller_profiles as seller_profile_service

router = APIRouter()


@router.get("/profile", response_model=SellerProfileRead)
def get_profile(current_user: CurrentUser, db: DbSession) -> SellerProfileRead:
    profile = seller_profile_service.get_seller_profile(db, user=current_user)
    if profile is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "seller_profile_not_found", "Seller profile was not found.")
    return SellerProfileRead.model_validate(profile)


@router.put("/profile", response_model=SellerProfileRead)
def upsert_profile(payload: SellerProfileUpsert, current_user: CurrentUser, db: DbSession) -> SellerProfileRead:
    profile = seller_profile_service.upsert_seller_profile(db, user=current_user, payload=payload)
    db.commit()
    db.refresh(profile)
    return SellerProfileRead.model_validate(profile)
