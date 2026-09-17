from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Category, Product


def list_categories(db: Session) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name)).all())


def list_products(db: Session, *, limit: int, offset: int) -> tuple[list[Product], int]:
    base = select(Product).options(selectinload(Product.category)).order_by(Product.created_at.desc(), Product.name)
    total = db.scalar(select(func.count()).select_from(Product)) or 0
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
        .where(Product.category_id == category.id)
        .options(selectinload(Product.category))
        .order_by(Product.created_at.desc(), Product.name)
    )
    total = db.scalar(select(func.count()).select_from(Product).where(Product.category_id == category.id)) or 0
    return category, list(db.scalars(query.limit(limit).offset(offset)).all()), total


def get_product_by_slug(db: Session, slug: str) -> Product | None:
    return db.scalar(
        select(Product)
        .where(Product.slug == slug)
        .options(selectinload(Product.category), selectinload(Product.variants))
    )


def search_products(db: Session, *, query: str, limit: int, offset: int) -> tuple[list[Product], int]:
    pattern = f"%{query.strip()}%"
    criteria = or_(
        Product.name.ilike(pattern),
        Product.slug.ilike(pattern),
        Product.brand.ilike(pattern),
        Product.description.ilike(pattern),
    )
    base = select(Product).where(criteria).options(selectinload(Product.category)).order_by(Product.name)
    total = db.scalar(select(func.count()).select_from(Product).where(criteria)) or 0
    return list(db.scalars(base.limit(limit).offset(offset)).all()), total

