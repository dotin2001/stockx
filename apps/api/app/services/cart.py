from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.errors import APIError
from app.models import CartItem, Listing, Product, User
from app.schemas.cart import CartItemRead, CartListingRead, GuestCartItemRead, GuestCartSkippedItem
from app.services.integrity import matches_integrity_target
from app.services.customer_lock import lock_customer_row


CART_ITEM_LOAD_OPTIONS = (
    selectinload(CartItem.listing).selectinload(Listing.product).selectinload(Product.category),
)
LISTING_LOAD_OPTIONS = (selectinload(Listing.product).selectinload(Product.category),)
CART_DUPLICATE_TARGETS = ("uq_cart_items_user_id_listing_id", "cart_items.user_id, cart_items.listing_id")


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


def _availability_reason(listing: Listing) -> str | None:
    if listing.product.archived_at is not None:
        return "product_archived"
    if listing.status != "active":
        return f"listing_{listing.status}"
    if listing.available_quantity <= 0:
        return "inventory_unavailable"
    return None


def _availability_reason_for_quantity(listing: Listing, quantity: int) -> str | None:
    unavailable_reason = _availability_reason(listing)
    if unavailable_reason is not None:
        return unavailable_reason
    if quantity > listing.available_quantity:
        return "quantity_limited"
    return None


def _require_listing_available(listing: Listing, *, quantity: int) -> None:
    unavailable_reason = _availability_reason(listing)
    if unavailable_reason == "product_archived":
        raise APIError(status.HTTP_409_CONFLICT, "product_archived", "Product is no longer available.")
    if unavailable_reason is not None:
        raise APIError(status.HTTP_409_CONFLICT, "listing_unavailable", "Listing is no longer available.")
    if quantity > listing.available_quantity:
        raise APIError(
            status.HTTP_409_CONFLICT,
            "quantity_exceeds_availability",
            "Requested quantity exceeds available inventory.",
        )


def _load_user_cart_item(db: Session, *, user: User, item_id: UUID) -> CartItem:
    item = db.scalar(select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user.id).options(*CART_ITEM_LOAD_OPTIONS))
    if item is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "cart_item_not_found", "Cart item was not found.")
    return item


def list_cart_items(db: Session, *, user: User) -> list[CartItem]:
    return list(db.scalars(_cart_item_query(user)).all())


def add_cart_item(
    db: Session,
    *,
    user: User,
    listing_id: UUID,
    quantity: int,
    _customer_locked: bool = False,
) -> CartItem:
    if not _customer_locked:
        lock_customer_row(db, user.id)
    user_id = user.id
    listing = _load_listing(db, listing_id)

    item = db.scalar(
        select(CartItem)
        .where(CartItem.user_id == user.id, CartItem.listing_id == listing.id)
        .options(*CART_ITEM_LOAD_OPTIONS)
        .execution_options(populate_existing=True)
    )
    if item is None:
        _require_listing_available(listing, quantity=quantity)
        item = CartItem(user_id=user.id, listing_id=listing.id, quantity=quantity)
        db.add(item)
    else:
        _require_listing_available(listing, quantity=item.quantity + quantity)
        item.quantity += quantity

    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if not matches_integrity_target(exc, CART_DUPLICATE_TARGETS):
            raise
        item = db.scalar(
            select(CartItem)
            .where(CartItem.user_id == user_id, CartItem.listing_id == listing_id)
            .options(*CART_ITEM_LOAD_OPTIONS)
            .execution_options(populate_existing=True)
        )
        if item is None:
            raise APIError(status.HTTP_409_CONFLICT, "cart_item_duplicate", "Cart item already exists.") from exc
        _require_listing_available(listing, quantity=item.quantity + quantity)
        item.quantity += quantity
        db.flush()
    return _load_user_cart_item(db, user=user, item_id=item.id)


def update_cart_item(db: Session, *, user: User, item_id: UUID, quantity: int) -> CartItem:
    lock_customer_row(db, user.id)
    item = _load_user_cart_item(db, user=user, item_id=item_id)
    _require_listing_available(item.listing, quantity=quantity)
    item.quantity = quantity
    db.flush()
    return _load_user_cart_item(db, user=user, item_id=item.id)


def remove_cart_item(db: Session, *, user: User, item_id: UUID) -> None:
    lock_customer_row(db, user.id)
    item = _load_user_cart_item(db, user=user, item_id=item_id)
    db.delete(item)


def resolve_guest_cart_items(db: Session, *, items: list[tuple[UUID, int]]) -> tuple[list[GuestCartItemRead], list[GuestCartSkippedItem]]:
    resolved: list[GuestCartItemRead] = []
    skipped: list[GuestCartSkippedItem] = []
    for listing_id, quantity in items:
        listing = db.scalar(select(Listing).where(Listing.id == listing_id).options(*LISTING_LOAD_OPTIONS))
        if listing is None:
            reason = "listing_not_found"
            resolved.append(GuestCartItemRead(listing_id=listing_id, quantity=quantity, available=False, unavailable_reason=reason, listing=None))
            skipped.append(GuestCartSkippedItem(listing_id=listing_id, quantity=quantity, reason=reason))
            continue

        reason = _availability_reason_for_quantity(listing, quantity)
        resolved.append(
            GuestCartItemRead(
                listing_id=listing.id,
                quantity=quantity,
                available=reason is None,
                unavailable_reason=reason,
                listing=CartListingRead.model_validate(listing),
            )
        )
        if reason is not None:
            skipped.append(GuestCartSkippedItem(listing_id=listing.id, quantity=quantity, reason=reason))
    return resolved, skipped


def merge_guest_cart_items(db: Session, *, user: User, items: list[tuple[UUID, int]]) -> tuple[list[CartItem], list[GuestCartSkippedItem]]:
    lock_customer_row(db, user.id)
    skipped: list[GuestCartSkippedItem] = []
    for listing_id, quantity in items:
        listing = db.scalar(select(Listing).where(Listing.id == listing_id).options(*LISTING_LOAD_OPTIONS))
        if listing is None:
            skipped.append(GuestCartSkippedItem(listing_id=listing_id, quantity=quantity, reason="listing_not_found"))
            continue

        reason = _availability_reason_for_quantity(listing, quantity)
        if reason is not None:
            skipped.append(GuestCartSkippedItem(listing_id=listing.id, quantity=quantity, reason=reason))
            continue

        add_cart_item(db, user=user, listing_id=listing.id, quantity=quantity, _customer_locked=True)
    return list_cart_items(db, user=user), skipped


def serialize_cart_item(item: CartItem) -> CartItemRead:
    listing = item.listing
    unavailable_reason = _availability_reason_for_quantity(listing, item.quantity)

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
