from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.cart import CartItemAdd, CartItemRead, CartItemUpdate, CartMergeResponse, CartRead, GuestCartRead, GuestCartResolveRequest
from app.services import cart as cart_service

router = APIRouter()


def _cart_response(items) -> CartRead:
    serialized = [cart_service.serialize_cart_item(item) for item in items]
    return CartRead(items=serialized, total_quantity=sum(item.quantity for item in serialized))


@router.get("", response_model=CartRead)
def get_cart(current_user: CurrentUser, db: DbSession) -> CartRead:
    return _cart_response(cart_service.list_cart_items(db, user=current_user))


@router.post("/guest/resolve", response_model=GuestCartRead)
def resolve_guest_cart(payload: GuestCartResolveRequest, db: DbSession) -> GuestCartRead:
    items, skipped = cart_service.resolve_guest_cart_items(
        db,
        items=[(item.listing_id, item.quantity) for item in payload.items],
    )
    return GuestCartRead(items=items, total_quantity=sum(item.quantity for item in items if item.available), skipped=skipped)


@router.post("/items", response_model=CartItemRead, status_code=status.HTTP_201_CREATED)
def add_cart_item(payload: CartItemAdd, current_user: CurrentUser, db: DbSession) -> CartItemRead:
    item = cart_service.add_cart_item(db, user=current_user, listing_id=payload.listing_id, quantity=payload.quantity)
    db.commit()
    return cart_service.serialize_cart_item(item)


@router.post("/merge", response_model=CartMergeResponse)
def merge_guest_cart(payload: GuestCartResolveRequest, current_user: CurrentUser, db: DbSession) -> CartMergeResponse:
    items, skipped = cart_service.merge_guest_cart_items(
        db,
        user=current_user,
        items=[(item.listing_id, item.quantity) for item in payload.items],
    )
    db.commit()
    return CartMergeResponse(cart=_cart_response(items), skipped=skipped)


@router.patch("/items/{item_id}", response_model=CartItemRead)
def update_cart_item(item_id: UUID, payload: CartItemUpdate, current_user: CurrentUser, db: DbSession) -> CartItemRead:
    item = cart_service.update_cart_item(db, user=current_user, item_id=item_id, quantity=payload.quantity)
    db.commit()
    return cart_service.serialize_cart_item(item)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_cart_item(item_id: UUID, current_user: CurrentUser, db: DbSession) -> None:
    cart_service.remove_cart_item(db, user=current_user, item_id=item_id)
    db.commit()
    return None
