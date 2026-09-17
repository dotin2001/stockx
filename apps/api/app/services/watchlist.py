from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.errors import APIError
from app.models import Product, User, WatchlistItem


def list_watchlist(db: Session, *, user: User) -> list[WatchlistItem]:
    return list(
        db.scalars(
            select(WatchlistItem)
            .where(WatchlistItem.user_id == user.id)
            .options(selectinload(WatchlistItem.product).selectinload(Product.category))
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
        raise APIError(status.HTTP_409_CONFLICT, "watchlist_duplicate", "Product is already in the watchlist.")

    item = WatchlistItem(user_id=user.id, product_id=product_id)
    db.add(item)
    db.flush()
    db.refresh(item, attribute_names=["product"])
    return item


def remove_watchlist_item(db: Session, *, user: User, item_id: UUID) -> None:
    item = db.scalar(
        select(WatchlistItem).where(
            WatchlistItem.id == item_id,
            WatchlistItem.user_id == user.id,
        )
    )
    if item is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "watchlist_item_not_found", "Watchlist item was not found.")
    db.delete(item)
