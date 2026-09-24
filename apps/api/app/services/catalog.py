from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Category, Listing, Product


def list_categories(db: Session) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name)).all())


def list_products(db: Session, *, limit: int, offset: int) -> tuple[list[Product], int]:
    active = Product.archived_at.is_(None)
    base = select(Product).where(active).options(selectinload(Product.category)).order_by(Product.created_at.desc(), Product.name)
    total = db.scalar(select(func.count()).select_from(Product).where(active)) or 0
    products = list(db.scalars(base.limit(limit).offset(offset)).all())
    return products, total


def get_category_by_slug(db: Session, slug: str) -> Category | None:
    return db.scalar(select(Category).where(Category.slug == slug))


def list_products_for_category(db: Session, *, slug: str, limit: int, offset: int) -> tuple[Category | None, list[Product], int]:
    category = get_category_by_slug(db, slug)
    if category is None:
        return None, [], 0

    query = (
        select(Product)
        .where(Product.category_id == category.id, Product.archived_at.is_(None))
        .options(selectinload(Product.category))
        .order_by(Product.created_at.desc(), Product.name)
    )
    total = db.scalar(
        select(func.count()).select_from(Product).where(Product.category_id == category.id, Product.archived_at.is_(None))
    ) or 0
    return category, list(db.scalars(query.limit(limit).offset(offset)).all()), total


def get_product_by_slug(db: Session, slug: str) -> Product | None:
    return db.scalar(
        select(Product)
        .where(Product.slug == slug, Product.archived_at.is_(None))
        .options(selectinload(Product.category), selectinload(Product.variants))
        .execution_options(populate_existing=True)
    )


def get_lowest_active_listing_for_product(db: Session, product: Product) -> Listing | None:
    if product.archived_at is not None:
        return None
    return db.scalar(
        select(Listing)
        .where(
            Listing.product_id == product.id,
            Listing.status == "active",
        )
        .order_by(Listing.price_cents.asc(), Listing.created_at.asc(), Listing.id.asc())
        .limit(1)
    )


def search_products(db: Session, *, query: str, limit: int, offset: int) -> tuple[list[Product], int]:
    pattern = f"%{query.strip()}%"
    criteria = or_(
        Product.name.ilike(pattern),
        Product.slug.ilike(pattern),
        Product.brand.ilike(pattern),
        Product.description.ilike(pattern),
    )
    active_criteria = (criteria, Product.archived_at.is_(None))
    base = select(Product).where(*active_criteria).options(selectinload(Product.category)).order_by(Product.name)
    total = db.scalar(select(func.count()).select_from(Product).where(*active_criteria)) or 0
    return list(db.scalars(base.limit(limit).offset(offset)).all()), total
