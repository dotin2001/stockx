from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentAdminUser, DbSession
from app.schemas.listing import ListingCreate, ListingManagementRead, ListingPage, ListingRead
from app.services import listings as listing_service

router = APIRouter()


@router.get("", response_model=ListingPage)
def list_my_listings(
    current_user: CurrentAdminUser,
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ListingPage:
    listings, total = listing_service.list_user_listings(db, user=current_user, limit=limit, offset=offset)
    return ListingPage(
        items=[ListingManagementRead.model_validate(listing) for listing in listings],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ListingRead, status_code=status.HTTP_201_CREATED)
def create_listing(payload: ListingCreate, current_user: CurrentAdminUser, db: DbSession) -> ListingRead:
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


@router.post("/{listing_id}/cancel", response_model=ListingManagementRead)
def cancel_listing(listing_id: UUID, current_user: CurrentAdminUser, db: DbSession) -> ListingManagementRead:
    listing = listing_service.cancel_user_listing(db, user=current_user, listing_id=listing_id)
    db.commit()
    return ListingManagementRead.model_validate(listing)
