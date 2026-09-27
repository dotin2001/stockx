from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import selectinload

from app.api.errors import APIError
from app.models import Listing, Product, ProductVariant, User
LISTING_LOAD_OPTIONS = (selectinload(Listing.product).selectinload(Product.category),)
MANAGED_LISTING_LOAD_OPTIONS = (
    selectinload(Listing.product).selectinload(Product.category),
    selectinload(Listing.product_variant),
)
LISTING_STATUSES = {"active", "sold", "cancelled"}


def create_listing(
    db: Session,
    *,
    user: User,
    product_id,
    product_variant_id,
    price_cents: int,
    currency: str,
) -> Listing:
    if not user.is_admin:
        raise APIError(status.HTTP_403_FORBIDDEN, "store_managed_listings", "Listings are managed by the store admin.")

    product = db.get(Product, product_id)
    if product is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "product_not_found", "Product was not found.")
    if product.archived_at is not None:
        raise APIError(status.HTTP_409_CONFLICT, "product_archived", "Product is no longer available.")

    if product_variant_id is not None:
        variant = db.get(ProductVariant, product_variant_id)
        if variant is None or variant.product_id != product.id:
            raise APIError(status.HTTP_404_NOT_FOUND, "variant_not_found", "Product variant was not found.")

    listing = Listing(
        user_id=user.id,
        product_id=product.id,
        product_variant_id=product_variant_id,
        price_cents=price_cents,
        currency=currency.upper(),
        status="active",
    )
    db.add(listing)
    db.flush()
    return listing


def create_managed_listing(
    db: Session,
    *,
    actor: User,
    product_id: UUID,
    product_variant_id: UUID | None,
    price_cents: int,
    currency: str,
    available_quantity: int,
    listing_status: str,
) -> Listing:
    _require_supreme_admin(actor)
    if price_cents <= 0:
        raise APIError(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_listing_price", "Listing price must be greater than zero.")
    if available_quantity < 0:
        raise APIError(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_available_quantity", "Available quantity cannot be negative.")
    if listing_status not in LISTING_STATUSES:
        raise APIError(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_listing_status", "Listing status is invalid.")

    product = db.get(Product, product_id)
    if product is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "product_not_found", "Product was not found.")
    if product.archived_at is not None:
        raise APIError(status.HTTP_409_CONFLICT, "product_archived", "Product is no longer available.")

    if product_variant_id is not None:
        variant = db.get(ProductVariant, product_variant_id)
        if variant is None or variant.product_id != product.id:
            raise APIError(status.HTTP_404_NOT_FOUND, "variant_not_found", "Product variant was not found.")

    listing = Listing(
        user_id=actor.id,
        product_id=product.id,
        product_variant_id=product_variant_id,
        price_cents=price_cents,
        available_quantity=available_quantity,
        currency=currency.upper(),
        status=listing_status,
    )
    db.add(listing)
    db.flush()
    return _load_managed_listing(db, listing.id)


def list_user_listings(db: Session, *, user: User, limit: int, offset: int) -> tuple[list[Listing], int]:
    criteria = (Listing.user_id == user.id,)
    total = db.scalar(select(func.count()).select_from(Listing).where(*criteria)) or 0
    listings = list(
        db.scalars(
            select(Listing)
            .where(*criteria)
            .options(*LISTING_LOAD_OPTIONS)
            .order_by(Listing.created_at.desc())
            .limit(limit)
            .offset(offset)
            .execution_options(populate_existing=True)
        ).all()
    )
    return listings, total


def cancel_user_listing(db: Session, *, user: User, listing_id: UUID) -> Listing:
    listing = db.scalar(
        select(Listing)
        .where(Listing.id == listing_id, Listing.user_id == user.id)
        .options(*LISTING_LOAD_OPTIONS)
        .execution_options(populate_existing=True)
    )
    if listing is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "listing_not_found", "Listing was not found.")
    listing.status = "cancelled"
    db.flush()
    return listing


def list_managed_listings(
    db: Session,
    *,
    status_filter: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Listing], int]:
    criteria = []
    if status_filter is not None:
        criteria.append(Listing.status == status_filter)

    count_query = select(func.count()).select_from(Listing)
    query = select(Listing).options(*LISTING_LOAD_OPTIONS).order_by(Listing.created_at.desc(), Listing.id)
    for criterion in criteria:
        count_query = count_query.where(criterion)
        query = query.where(criterion)

    total = db.scalar(count_query) or 0
    listings = list(db.scalars(query.limit(limit).offset(offset).execution_options(populate_existing=True)).all())
    return listings, total


def cancel_managed_listing(db: Session, *, listing_id: UUID) -> Listing:
    listing = db.scalar(
        select(Listing)
        .where(Listing.id == listing_id)
        .options(*LISTING_LOAD_OPTIONS)
        .execution_options(populate_existing=True)
    )
    if listing is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "listing_not_found", "Listing was not found.")
    listing.status = "cancelled"
    db.flush()
    return listing


def _require_supreme_admin(actor: User) -> None:
    if not actor.is_supreme_admin:
        raise APIError(
            status.HTTP_403_FORBIDDEN,
            "supreme_admin_required",
            "Supreme admin access is required.",
        )


def _load_managed_listing(db: Session, listing_id: UUID) -> Listing:
    listing = db.scalar(
        select(Listing)
        .where(Listing.id == listing_id)
        .options(*MANAGED_LISTING_LOAD_OPTIONS)
        .execution_options(populate_existing=True)
    )
    if listing is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "listing_not_found", "Listing was not found.")
    return listing


def adjust_managed_listing_quantity(
    db: Session,
    *,
    listing_id: UUID,
    adjustment: int,
    actor: User,
) -> Listing:
    _require_supreme_admin(actor)
    if adjustment == 0:
        raise APIError(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_quantity_adjustment", "Quantity adjustment must be non-zero.")

    listing = _load_managed_listing(db, listing_id)
    next_quantity = listing.available_quantity + adjustment
    if next_quantity < 0:
        raise APIError(
            status.HTTP_409_CONFLICT,
            "inventory_quantity_below_zero",
            "Inventory quantity cannot be reduced below zero.",
        )

    listing.available_quantity = next_quantity
    db.flush()
    return _load_managed_listing(db, listing.id)


def change_managed_listing_status(
    db: Session,
    *,
    listing_id: UUID,
    next_status: str,
    actor: User,
) -> Listing:
    _require_supreme_admin(actor)
    if next_status not in LISTING_STATUSES:
        raise APIError(status.HTTP_422_UNPROCESSABLE_ENTITY, "invalid_listing_status", "Listing status is invalid.")

    listing = _load_managed_listing(db, listing_id)
    listing.status = next_status
    db.flush()
    return _load_managed_listing(db, listing.id)
