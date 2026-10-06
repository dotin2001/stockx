from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.cart import CartItemAdd, CartItemRead, CartItemUpdate, CartRead
from app.services import cart as cart_service

router = APIRouter()


def _cart_response(items) -> CartRead:
    serialized = [cart_service.serialize_cart_item(item) for item in items]
    return CartRead(items=serialized, total_quantity=sum(item.quantity for item in serialized))


@router.get("", response_model=CartRead)
def get_cart(current_user: CurrentUser, db: DbSession) -> CartRead:
    return _cart_response(cart_service.list_cart_items(db, user=current_user))


@router.post("/items", response_model=CartItemRead, status_code=status.HTTP_201_CREATED)
def add_cart_item(payload: CartItemAdd, current_user: CurrentUser, db: DbSession) -> CartItemRead:
    item = cart_service.add_cart_item(db, user=current_user, listing_id=payload.listing_id, quantity=payload.quantity)
    db.commit()
    return cart_service.serialize_cart_item(item)


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
