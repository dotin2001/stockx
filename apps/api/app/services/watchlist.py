from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.errors import APIError
from app.models import Product, User, WatchlistItem
from app.services.integrity import matches_integrity_target


WATCHLIST_DUPLICATE_TARGETS = ("uq_watchlist_items_user_id_product_id", "watchlist_items.user_id, watchlist_items.product_id")
WATCHLIST_LOAD_OPTIONS = (selectinload(WatchlistItem.product).selectinload(Product.category),)


def _watchlist_duplicate() -> APIError:
    return APIError(status.HTTP_409_CONFLICT, "watchlist_duplicate", "Product is already in the watchlist.")


def list_watchlist(db: Session, *, user: User) -> list[WatchlistItem]:
    return list(
        db.scalars(
            select(WatchlistItem)
            .where(WatchlistItem.user_id == user.id)
            .options(*WATCHLIST_LOAD_OPTIONS)
            .order_by(WatchlistItem.created_at.desc())
        ).all()
    )


def add_watchlist_item(db: Session, *, user: User, product_id: UUID) -> WatchlistItem:
    product = db.get(Product, product_id)
    if product is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "product_not_found", "Product was not found.")

    existing = db.scalar(
        select(WatchlistItem).where(
            WatchlistItem.user_id == user.id,
            WatchlistItem.product_id == product_id,
        )
    )
    if existing is not None:
        raise _watchlist_duplicate()

    item = WatchlistItem(user_id=user.id, product_id=product_id)
    db.add(item)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if matches_integrity_target(exc, WATCHLIST_DUPLICATE_TARGETS):
            raise _watchlist_duplicate() from exc
        raise
    return _load_user_watchlist_item(db, user=user, item_id=item.id)


def _load_user_watchlist_item(db: Session, *, user: User, item_id: UUID) -> WatchlistItem:
    item = db.scalar(
        select(WatchlistItem)
        .where(
            WatchlistItem.id == item_id,
            WatchlistItem.user_id == user.id,
        )
        .options(*WATCHLIST_LOAD_OPTIONS)
        .execution_options(populate_existing=True)
    )
    if item is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "watchlist_item_not_found", "Watchlist item was not found.")
    return item


def remove_watchlist_item(db: Session, *, user: User, item_id: UUID) -> None:
    item = _load_user_watchlist_item(db, user=user, item_id=item_id)
    db.delete(item)
