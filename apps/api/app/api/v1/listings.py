from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.listing import ListingCreate, ListingRead
from app.services import listings as listing_service

router = APIRouter()


@router.post("", response_model=ListingRead, status_code=status.HTTP_201_CREATED)
def create_listing(payload: ListingCreate, current_user: CurrentUser, db: DbSession) -> ListingRead:
    listing = listing_service.create_listing(
        db,
        user=current_user,
        product_id=payload.product_id,
        product_variant_id=payload.product_variant_id,
        price_cents=payload.price_cents,
        currency=payload.currency,
    )
    db.commit()
    db.refresh(listing)
    return ListingRead.model_validate(listing)

