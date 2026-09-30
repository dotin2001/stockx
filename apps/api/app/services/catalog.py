from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Select, and_, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Category, Listing, Product, ProductVariant
from app.schemas.product import (
    ProductDiscoveryFacetOption,
    ProductDiscoveryMetadata,
    ProductDiscoveryPriceBounds,
    ProductDiscoveryQuery,
    ProductDiscoverySelectedFilters,
    ProductDiscoverySort,
)


@dataclass(frozen=True)
class ProductDiscoveryResult:
    products: list[Product]
    total: int
    metadata: ProductDiscoveryMetadata


def list_categories(db: Session) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name)).all())


def _lowest_active_listing_prices():
    return (
        select(
            Listing.product_id.label("product_id"),
            func.min(Listing.price_cents).label("lowest_active_price_cents"),
        )
        .where(Listing.status == "active", Listing.available_quantity > 0)
        .group_by(Listing.product_id)
        .subquery()
    )


def _search_criterion(query: str):
    pattern = f"%{query.strip()}%"
    return or_(
        Product.name.ilike(pattern),
        Product.slug.ilike(pattern),
        Product.brand.ilike(pattern),
        Product.description.ilike(pattern),
    )


def _active_listing_exists(*extra_criteria):
    return exists(
        select(1).where(
            Listing.product_id == Product.id,
            Listing.status == "active",
            Listing.available_quantity > 0,
            *extra_criteria,
        )
    )


def _variant_size_exists(sizes: list[str]):
    return exists(
        select(1).where(
            ProductVariant.product_id == Product.id,
            ProductVariant.size.in_(sizes),
        )
    )


def _discovery_criteria(
    query: ProductDiscoveryQuery,
    *,
    include_brand: bool = True,
    include_size: bool = True,
    include_price: bool = True,
) -> list:
    criteria = [Product.archived_at.is_(None)]
    if query.category_slug:
        criteria.append(Product.category.has(Category.slug == query.category_slug))
    if query.q:
        criteria.append(_search_criterion(query.q))
    if include_brand and query.brands:
        criteria.append(Product.brand.in_(query.brands))
    if include_size and query.sizes:
        criteria.append(_variant_size_exists(query.sizes))
    if query.available_only:
        criteria.append(_active_listing_exists())
    if include_price and (query.min_price_cents is not None or query.max_price_cents is not None):
        price_criteria = []
        if query.min_price_cents is not None:
            price_criteria.append(Listing.price_cents >= query.min_price_cents)
        if query.max_price_cents is not None:
            price_criteria.append(Listing.price_cents <= query.max_price_cents)
        criteria.append(_active_listing_exists(*price_criteria))
    return criteria


def _ordered_statement(statement: Select[tuple[Product]], query: ProductDiscoveryQuery, lowest_prices) -> Select[tuple[Product]]:
    if query.sort == ProductDiscoverySort.PRICE_ASC:
        return statement.order_by(
            lowest_prices.c.lowest_active_price_cents.is_(None).asc(),
            lowest_prices.c.lowest_active_price_cents.asc(),
            Product.name.asc(),
            Product.id.asc(),
        )
    if query.sort == ProductDiscoverySort.PRICE_DESC:
        return statement.order_by(
            lowest_prices.c.lowest_active_price_cents.is_(None).asc(),
            lowest_prices.c.lowest_active_price_cents.desc(),
            Product.name.asc(),
            Product.id.asc(),
        )
    if query.sort == ProductDiscoverySort.POPULAR:
        return statement.order_by(Product.total_sold.desc(), Product.name.asc(), Product.id.asc())
    if query.sort == ProductDiscoverySort.NAME_ASC:
        return statement.order_by(Product.name.asc(), Product.id.asc())
    return statement.order_by(Product.created_at.desc(), Product.name.asc(), Product.id.asc())


def _count_products(db: Session, query: ProductDiscoveryQuery) -> int:
    count_statement = select(func.count(Product.id)).where(*_discovery_criteria(query))
    return db.scalar(count_statement) or 0


def _brand_options(db: Session, query: ProductDiscoveryQuery) -> list[ProductDiscoveryFacetOption]:
    rows = db.execute(
        select(Product.brand, func.count(Product.id))
        .where(Product.brand.is_not(None), *_discovery_criteria(query, include_brand=False))
        .group_by(Product.brand)
        .order_by(Product.brand.asc())
    ).all()
    return [
        ProductDiscoveryFacetOption(value=brand, label=brand, count=count)
        for brand, count in rows
        if brand
    ]


def _size_options(db: Session, query: ProductDiscoveryQuery) -> list[ProductDiscoveryFacetOption]:
    rows = db.execute(
        select(ProductVariant.size, func.count(func.distinct(Product.id)))
        .select_from(Product)
        .join(ProductVariant, ProductVariant.product_id == Product.id)
        .where(ProductVariant.size.is_not(None), *_discovery_criteria(query, include_size=False))
        .group_by(ProductVariant.size)
        .order_by(ProductVariant.size.asc())
    ).all()
    return [
        ProductDiscoveryFacetOption(value=size, label=size, count=count)
        for size, count in rows
        if size
    ]


def _price_bounds(db: Session, query: ProductDiscoveryQuery, lowest_prices) -> ProductDiscoveryPriceBounds:
    row = db.execute(
        select(
            func.min(lowest_prices.c.lowest_active_price_cents),
            func.max(lowest_prices.c.lowest_active_price_cents),
        )
        .select_from(Product)
        .join(lowest_prices, lowest_prices.c.product_id == Product.id)
        .where(*_discovery_criteria(query, include_price=False))
    ).one()
    min_cents, max_cents = row
    return ProductDiscoveryPriceBounds(min_cents=min_cents, max_cents=max_cents)


def _metadata(
    db: Session,
    *,
    query: ProductDiscoveryQuery,
    total: int,
    lowest_prices,
) -> ProductDiscoveryMetadata:
    return ProductDiscoveryMetadata(
        selected=ProductDiscoverySelectedFilters(
            q=query.q,
            category_slug=query.category_slug,
            brands=query.brands,
            sizes=query.sizes,
            min_price_cents=query.min_price_cents,
            max_price_cents=query.max_price_cents,
            available_only=query.available_only,
        ),
        sort=query.sort,
        brands=_brand_options(db, query),
        sizes=_size_options(db, query),
        price_bounds=_price_bounds(db, query, lowest_prices),
        total=total,
        limit=query.limit,
        offset=query.offset,
    )


def discover_products(db: Session, query: ProductDiscoveryQuery) -> ProductDiscoveryResult:
    lowest_prices = _lowest_active_listing_prices()
    base = (
        select(Product)
        .outerjoin(lowest_prices, lowest_prices.c.product_id == Product.id)
        .where(*_discovery_criteria(query))
        .options(selectinload(Product.category))
    )
    total = _count_products(db, query)
    products = list(
        db.scalars(
            _ordered_statement(base, query, lowest_prices)
            .limit(query.limit)
            .offset(query.offset)
        ).all()
    )
    return ProductDiscoveryResult(
        products=products,
        total=total,
        metadata=_metadata(db, query=query, total=total, lowest_prices=lowest_prices),
    )


def list_products(db: Session, *, limit: int, offset: int) -> tuple[list[Product], int]:
    result = discover_products(db, ProductDiscoveryQuery(limit=limit, offset=offset))
    return result.products, result.total


def get_category_by_slug(db: Session, slug: str) -> Category | None:
    return db.scalar(select(Category).where(Category.slug == slug))


def list_products_for_category(db: Session, *, slug: str, limit: int, offset: int) -> tuple[Category | None, list[Product], int]:
    category = get_category_by_slug(db, slug)
    if category is None:
        return None, [], 0

    result = discover_products(db, ProductDiscoveryQuery(category_slug=slug, limit=limit, offset=offset))
    return category, result.products, result.total


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
            Listing.available_quantity > 0,
        )
        .order_by(Listing.price_cents.asc(), Listing.created_at.asc(), Listing.id.asc())
        .limit(1)
    )


def search_products(db: Session, *, query: str, limit: int, offset: int) -> tuple[list[Product], int]:
    result = discover_products(db, ProductDiscoveryQuery(q=query, limit=limit, offset=offset, sort=ProductDiscoverySort.NAME_ASC))
    return result.products, result.total
