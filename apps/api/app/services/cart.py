from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.errors import APIError
from app.models import CartItem, Listing, Product, User
from app.schemas.cart import CartItemRead, CartListingRead


CART_ITEM_LOAD_OPTIONS = (
    selectinload(CartItem.listing).selectinload(Listing.product).selectinload(Product.category),
)
LISTING_LOAD_OPTIONS = (selectinload(Listing.product).selectinload(Product.category),)


def _cart_item_query(user: User):
    return (
        select(CartItem)
        .where(CartItem.user_id == user.id)
        .options(*CART_ITEM_LOAD_OPTIONS)
        .order_by(CartItem.created_at.desc())
        .execution_options(populate_existing=True)
    )


def _load_listing(db: Session, listing_id: UUID) -> Listing:
    listing = db.scalar(select(Listing).where(Listing.id == listing_id).options(*LISTING_LOAD_OPTIONS))
    if listing is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "listing_not_found", "Listing was not found.")
    return listing


def _require_listing_available(listing: Listing) -> None:
    if listing.product.archived_at is not None:
        raise APIError(status.HTTP_409_CONFLICT, "product_archived", "Product is no longer available.")
    if listing.status != "active":
        raise APIError(status.HTTP_409_CONFLICT, "listing_unavailable", "Listing is no longer available.")


def _load_user_cart_item(db: Session, *, user: User, item_id: UUID) -> CartItem:
    item = db.scalar(select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user.id).options(*CART_ITEM_LOAD_OPTIONS))
    if item is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "cart_item_not_found", "Cart item was not found.")
    return item


def list_cart_items(db: Session, *, user: User) -> list[CartItem]:
    return list(db.scalars(_cart_item_query(user)).all())


def add_cart_item(db: Session, *, user: User, listing_id: UUID, quantity: int) -> CartItem:
    listing = _load_listing(db, listing_id)
    _require_listing_available(listing)

    item = db.scalar(
        select(CartItem)
        .where(CartItem.user_id == user.id, CartItem.listing_id == listing.id)
        .options(*CART_ITEM_LOAD_OPTIONS)
        .execution_options(populate_existing=True)
    )
    if item is None:
        item = CartItem(user_id=user.id, listing_id=listing.id, quantity=quantity)
        db.add(item)
    else:
        item.quantity += quantity

    db.flush()
    return _load_user_cart_item(db, user=user, item_id=item.id)


def update_cart_item(db: Session, *, user: User, item_id: UUID, quantity: int) -> CartItem:
    item = _load_user_cart_item(db, user=user, item_id=item_id)
    item.quantity = quantity
    db.flush()
    return _load_user_cart_item(db, user=user, item_id=item.id)


def remove_cart_item(db: Session, *, user: User, item_id: UUID) -> None:
    item = _load_user_cart_item(db, user=user, item_id=item_id)
    db.delete(item)


def serialize_cart_item(item: CartItem) -> CartItemRead:
    listing = item.listing
    unavailable_reason = None
    if listing.product.archived_at is not None:
        unavailable_reason = "product_archived"
    elif listing.status != "active":
        unavailable_reason = f"listing_{listing.status}"

    return CartItemRead(
        id=item.id,
        listing_id=item.listing_id,
        quantity=item.quantity,
        available=unavailable_reason is None,
        unavailable_reason=unavailable_reason,
        listing=CartListingRead.model_validate(listing),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )
