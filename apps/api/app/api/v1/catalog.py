from typing import Annotated

from fastapi import APIRouter, Query, status
from pydantic import ValidationError

from app.api.deps import DbSession
from app.api.errors import APIError
from app.schemas.category import CategoryRead
from app.schemas.product import (
    ProductDetail,
    ProductDiscoveryQuery,
    ProductDiscoverySort,
    ProductPage,
)
from app.services import catalog as catalog_service

router = APIRouter()


@router.get("/categories", response_model=list[CategoryRead])
def list_categories(db: DbSession) -> list[CategoryRead]:
    return [CategoryRead.model_validate(category) for category in catalog_service.list_categories(db)]


def _discovery_query(
    *,
    limit: int,
    offset: int,
    q: str | None = None,
    category_slug: str | None = None,
    brand: list[str] | None = None,
    size: list[str] | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    available_only: bool = False,
    sort: ProductDiscoverySort = ProductDiscoverySort.NEWEST,
) -> ProductDiscoveryQuery:
    try:
        return ProductDiscoveryQuery(
            q=q,
            category_slug=category_slug,
            brands=brand or [],
            sizes=size or [],
            min_price_cents=min_price,
            max_price_cents=max_price,
            available_only=available_only,
            sort=sort,
            limit=limit,
            offset=offset,
        )
    except ValidationError as exc:
        raise APIError(status.HTTP_422_UNPROCESSABLE_ENTITY, "validation_error", "Request validation failed.") from exc


def _product_page(result: catalog_service.ProductDiscoveryResult) -> ProductPage:
    return ProductPage(
        items=[catalog_service.serialize_product_summary(product) for product in result.products],
        total=result.total,
        limit=result.metadata.limit,
        offset=result.metadata.offset,
        discovery=result.metadata,
    )


@router.get("/products", response_model=ProductPage)
def list_products(
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, min_length=1),
    brand: Annotated[list[str] | None, Query()] = None,
    size: Annotated[list[str] | None, Query()] = None,
    min_price: int | None = Query(default=None, ge=0),
    max_price: int | None = Query(default=None, ge=0),
    available_only: bool = Query(default=False),
    sort: ProductDiscoverySort = Query(default=ProductDiscoverySort.NEWEST),
) -> ProductPage:
    query = _discovery_query(
        q=q,
        brand=brand,
        size=size,
        min_price=min_price,
        max_price=max_price,
        available_only=available_only,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return _product_page(catalog_service.discover_products(db, query))


@router.get("/categories/{slug}/products", response_model=ProductPage)
def list_category_products(
    slug: str,
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None, min_length=1),
    brand: Annotated[list[str] | None, Query()] = None,
    size: Annotated[list[str] | None, Query()] = None,
    min_price: int | None = Query(default=None, ge=0),
    max_price: int | None = Query(default=None, ge=0),
    available_only: bool = Query(default=False),
    sort: ProductDiscoverySort = Query(default=ProductDiscoverySort.NEWEST),
) -> ProductPage:
    category = catalog_service.get_category_by_slug(db, slug)
    if category is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "category_not_found", "Category was not found.")
    query = _discovery_query(
        q=q,
        category_slug=slug,
        brand=brand,
        size=size,
        min_price=min_price,
        max_price=max_price,
        available_only=available_only,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return _product_page(catalog_service.discover_products(db, query))


@router.get("/products/{slug}", response_model=ProductDetail)
def get_product(slug: str, db: DbSession) -> ProductDetail:
    product = catalog_service.get_product_by_slug(db, slug)
    if product is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "product_not_found", "Product was not found.")
    return catalog_service.serialize_product_detail(db, product)


@router.get("/search", response_model=ProductPage)
def search_products(
    db: DbSession,
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    brand: Annotated[list[str] | None, Query()] = None,
    size: Annotated[list[str] | None, Query()] = None,
    min_price: int | None = Query(default=None, ge=0),
    max_price: int | None = Query(default=None, ge=0),
    available_only: bool = Query(default=False),
    sort: ProductDiscoverySort = Query(default=ProductDiscoverySort.NAME_ASC),
) -> ProductPage:
    query = _discovery_query(
        q=q,
        brand=brand,
        size=size,
        min_price=min_price,
        max_price=max_price,
        available_only=available_only,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return _product_page(catalog_service.discover_products(db, query))
