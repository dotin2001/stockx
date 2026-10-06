from fastapi import APIRouter, Query, status

from app.api.deps import DbSession
from app.api.errors import APIError
from app.schemas.category import CategoryRead
from app.schemas.product import ProductDetail, ProductPage, ProductSummary
from app.services import catalog as catalog_service

router = APIRouter()


@router.get("/categories", response_model=list[CategoryRead])
def list_categories(db: DbSession) -> list[CategoryRead]:
    return [CategoryRead.model_validate(category) for category in catalog_service.list_categories(db)]


@router.get("/products", response_model=ProductPage)
def list_products(
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ProductPage:
    products, total = catalog_service.list_products(db, limit=limit, offset=offset)
    return ProductPage(
        items=[ProductSummary.model_validate(product) for product in products],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/categories/{slug}/products", response_model=ProductPage)
def list_category_products(
    slug: str,
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ProductPage:
    category, products, total = catalog_service.list_products_for_category(db, slug=slug, limit=limit, offset=offset)
    if category is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "category_not_found", "Category was not found.")
    return ProductPage(
        items=[ProductSummary.model_validate(product) for product in products],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/products/{slug}", response_model=ProductDetail)
def get_product(slug: str, db: DbSession) -> ProductDetail:
    product = catalog_service.get_product_by_slug(db, slug)
    if product is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "product_not_found", "Product was not found.")
    return ProductDetail.model_validate(product)


@router.get("/search", response_model=ProductPage)
def search_products(
    db: DbSession,
    q: str = Query(min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> ProductPage:
    products, total = catalog_service.search_products(db, query=q, limit=limit, offset=offset)
    return ProductPage(
        items=[ProductSummary.model_validate(product) for product in products],
        total=total,
        limit=limit,
        offset=offset,
    )

