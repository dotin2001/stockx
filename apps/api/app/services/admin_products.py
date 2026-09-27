from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.errors import APIError
from app.models import Category, Listing, Product, ProductVariant, User
from app.schemas.product import (
    AdminProductInventoryItem,
    AdminProductInventorySummary,
    AdminProductRead,
    ActiveListingSummary,
    ProductCreate,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantRead,
    ProductVariantUpdate,
)
from app.services.integrity import matches_integrity_target


PRODUCT_LOAD_OPTIONS = (
    selectinload(Product.category),
    selectinload(Product.variants),
    selectinload(Product.listings).selectinload(Listing.product_variant),
)
PRODUCT_SLUG_TARGETS = ("uq_products_slug", "ix_products_slug", "products.slug")


def _product_slug_conflict() -> APIError:
    return APIError(status.HTTP_409_CONFLICT, "product_slug_exists", "A product already exists with this slug.")


def _load_product(db: Session, product_id: UUID) -> Product | None:
    return db.scalar(select(Product).where(Product.id == product_id).options(*PRODUCT_LOAD_OPTIONS))


def _ensure_category(db: Session, category_id: UUID) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "category_not_found", "Category was not found.")
    return category


def _ensure_unique_slug(db: Session, slug: str, *, excluding_product_id: UUID | None = None) -> None:
    query = select(Product).where(Product.slug == slug)
    if excluding_product_id is not None:
        query = query.where(Product.id != excluding_product_id)
    if db.scalar(query) is not None:
        raise _product_slug_conflict()


def list_managed_products(
    db: Session,
    *,
    archived: bool | None,
    limit: int,
    offset: int,
) -> tuple[list[Product], int]:
    criteria = []
    if archived is True:
        criteria.append(Product.archived_at.is_not(None))
    elif archived is False:
        criteria.append(Product.archived_at.is_(None))

    base = select(Product).options(*PRODUCT_LOAD_OPTIONS).order_by(Product.created_at.desc(), Product.name)
    count_query = select(func.count()).select_from(Product)
    for criterion in criteria:
        base = base.where(criterion)
        count_query = count_query.where(criterion)

    total = db.scalar(count_query) or 0
    products = list(db.scalars(base.limit(limit).offset(offset)).all())
    return products, total


def serialize_admin_product(product: Product) -> AdminProductRead:
    active_available_listings = [
        listing for listing in product.listings if listing.status == "active" and listing.available_quantity > 0
    ]
    inventory_items = [
        AdminProductInventoryItem(
            id=listing.id,
            user_id=listing.user_id,
            product_variant_id=listing.product_variant_id,
            variant=ProductVariantRead.model_validate(listing.product_variant) if listing.product_variant else None,
            price_cents=listing.price_cents,
            available_quantity=listing.available_quantity,
            currency=listing.currency,
            status=listing.status,
            created_at=listing.created_at,
            updated_at=listing.updated_at,
        )
        for listing in sorted(product.listings, key=lambda item: (item.created_at, str(item.id)), reverse=True)
    ]
    lowest_active_listing = min(
        active_available_listings,
        key=lambda item: (item.price_cents, item.created_at, str(item.id)),
        default=None,
    )

    return AdminProductRead(
        id=product.id,
        name=product.name,
        slug=product.slug,
        brand=product.brand,
        image_url=product.image_url,
        lowest_ask_cents=product.lowest_ask_cents,
        total_sold=product.total_sold,
        category=product.category,
        created_at=product.created_at,
        updated_at=product.updated_at,
        description=product.description,
        variants=[ProductVariantRead.model_validate(variant) for variant in product.variants],
        lowest_active_listing=ActiveListingSummary.model_validate(lowest_active_listing) if lowest_active_listing else None,
        archived_at=product.archived_at,
        archived_by_user_id=product.archived_by_user_id,
        inventory_summary=AdminProductInventorySummary(
            total_listings=len(product.listings),
            active_listings=sum(1 for listing in product.listings if listing.status == "active"),
            total_available_quantity=sum(
                listing.available_quantity for listing in product.listings if listing.status == "active"
            ),
            lowest_active_price_cents=lowest_active_listing.price_cents if lowest_active_listing else None,
        ),
        inventory_items=inventory_items,
    )


def create_product(db: Session, payload: ProductCreate) -> Product:
    _ensure_category(db, payload.category_id)
    _ensure_unique_slug(db, payload.slug)
    product = Product(**payload.model_dump())
    db.add(product)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if matches_integrity_target(exc, PRODUCT_SLUG_TARGETS):
            raise _product_slug_conflict() from exc
        raise
    return _load_product(db, product.id) or product


def update_product(db: Session, *, product_id: UUID, payload: ProductUpdate) -> Product:
    product = _load_product(db, product_id)
    if product is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "product_not_found", "Product was not found.")

    values = payload.model_dump(exclude_unset=True)
    category_id = values.get("category_id")
    if category_id is not None:
        _ensure_category(db, category_id)
    slug = values.get("slug")
    if slug is not None:
        _ensure_unique_slug(db, slug, excluding_product_id=product.id)

    for field, value in values.items():
        setattr(product, field, value)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if matches_integrity_target(exc, PRODUCT_SLUG_TARGETS):
            raise _product_slug_conflict() from exc
        raise
    return _load_product(db, product.id) or product


def archive_product(db: Session, *, product_id: UUID, admin: User) -> Product:
    product = _load_product(db, product_id)
    if product is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "product_not_found", "Product was not found.")
    product.archived_at = datetime.now(UTC)
    product.archived_by_user_id = admin.id
    db.flush()
    return _load_product(db, product.id) or product


def restore_product(db: Session, *, product_id: UUID) -> Product:
    product = _load_product(db, product_id)
    if product is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "product_not_found", "Product was not found.")
    product.archived_at = None
    product.archived_by_user_id = None
    db.flush()
    return _load_product(db, product.id) or product


def create_variant(db: Session, *, product_id: UUID, payload: ProductVariantCreate) -> ProductVariant:
    product = _load_product(db, product_id)
    if product is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "product_not_found", "Product was not found.")
    variant = ProductVariant(product_id=product.id, **payload.model_dump())
    db.add(variant)
    db.flush()
    return variant


def update_variant(db: Session, *, variant_id: UUID, payload: ProductVariantUpdate) -> ProductVariant:
    variant = db.get(ProductVariant, variant_id)
    if variant is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "variant_not_found", "Product variant was not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(variant, field, value)
    db.flush()
    return variant


def delete_variant(db: Session, *, variant_id: UUID) -> None:
    variant = db.get(ProductVariant, variant_id)
    if variant is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "variant_not_found", "Product variant was not found.")
    db.delete(variant)
