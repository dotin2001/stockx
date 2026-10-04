from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.category import CategoryRead


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _is_http_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


class ProductDiscoverySort(StrEnum):
    NEWEST = "newest"
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    POPULAR = "popular"
    NAME_ASC = "name_asc"


class ProductDiscoveryQuery(BaseModel):
    q: str | None = Field(default=None, min_length=1)
    category_slug: str | None = None
    brands: list[str] = Field(default_factory=list)
    sizes: list[str] = Field(default_factory=list)
    min_price_cents: int | None = Field(default=None, ge=0)
    max_price_cents: int | None = Field(default=None, ge=0)
    available_only: bool = False
    sort: ProductDiscoverySort = ProductDiscoverySort.NEWEST
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)

    @field_validator("q", "category_slug", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("brands", "sizes", mode="before")
    @classmethod
    def normalize_string_list(cls, value: list[str] | str | None) -> list[str]:
        if value is None:
            return []
        values = value if isinstance(value, list) else [value]
        normalized: list[str] = []
        seen: set[str] = set()
        for item in values:
            text = str(item).strip()
            key = text.casefold()
            if text and key not in seen:
                normalized.append(text)
                seen.add(key)
        return normalized

    @model_validator(mode="after")
    def validate_price_range(self) -> "ProductDiscoveryQuery":
        if (
            self.min_price_cents is not None
            and self.max_price_cents is not None
            and self.min_price_cents > self.max_price_cents
        ):
            raise ValueError("min_price_cents cannot exceed max_price_cents.")
        return self


class ProductDiscoverySelectedFilters(BaseModel):
    q: str | None = None
    category_slug: str | None = None
    brands: list[str] = Field(default_factory=list)
    sizes: list[str] = Field(default_factory=list)
    min_price_cents: int | None = None
    max_price_cents: int | None = None
    available_only: bool = False


class ProductDiscoveryFacetOption(BaseModel):
    value: str
    label: str
    count: int = Field(ge=0)


class ProductDiscoveryPriceBounds(BaseModel):
    min_cents: int | None = None
    max_cents: int | None = None


class ProductDiscoveryMetadata(BaseModel):
    selected: ProductDiscoverySelectedFilters = Field(default_factory=ProductDiscoverySelectedFilters)
    sort: ProductDiscoverySort = ProductDiscoverySort.NEWEST
    brands: list[ProductDiscoveryFacetOption] = Field(default_factory=list)
    sizes: list[ProductDiscoveryFacetOption] = Field(default_factory=list)
    price_bounds: ProductDiscoveryPriceBounds = Field(default_factory=ProductDiscoveryPriceBounds)
    total: int = 0
    limit: int = 20
    offset: int = 0


class ProductVariantRead(BaseModel):
    id: UUID
    size: str | None = None
    color: str | None = None
    sku: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ActiveListingSummary(BaseModel):
    id: UUID
    price_cents: int
    available_quantity: int
    currency: str
    status: str
    product_variant_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductDetailRow(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=240)

    @field_validator("label", "value", mode="before")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return str(value).strip()


class ProductGalleryImage(BaseModel):
    url: str = Field(min_length=1, max_length=1000)
    alt: str | None = Field(default=None, max_length=255)

    @field_validator("url", mode="before")
    @classmethod
    def normalize_url(cls, value: str) -> str:
        return str(value).strip()

    @field_validator("url")
    @classmethod
    def require_http_url(cls, value: str) -> str:
        if not _is_http_url(value):
            raise ValueError("Gallery image URL must start with http:// or https://.")
        return value

    @field_validator("alt", mode="before")
    @classmethod
    def normalize_alt(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)


class ProductPurchaseOption(BaseModel):
    id: UUID
    product_variant_id: UUID | None = None
    variant: ProductVariantRead | None = None
    label: str
    price_cents: int
    available_quantity: int
    currency: str
    status: str
    is_available: bool


class ProductStats(BaseModel):
    total_sold: int
    available_size_count: int
    total_available_quantity: int
    stock_state: str
    category: str
    brand: str | None = None


class ProductVariantCreate(BaseModel):
    size: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, max_length=128)
    sku: str | None = Field(default=None, max_length=128)


class ProductVariantUpdate(BaseModel):
    size: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, max_length=128)
    sku: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def require_update(self) -> "ProductVariantUpdate":
        if self.size is None and self.color is None and self.sku is None:
            raise ValueError("At least one variant field must be provided.")
        return self


class ProductSummary(BaseModel):
    id: UUID
    name: str
    slug: str
    brand: str | None = None
    image_url: str | None = None
    lowest_ask_cents: int | None = None
    store_price_cents: int | None = None
    total_sold: int
    category: CategoryRead
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductDetail(ProductSummary):
    description: str | None = None
    variants: list[ProductVariantRead] = Field(default_factory=list)
    lowest_active_listing: ActiveListingSummary | None = None
    feature_bullets: list[str] = Field(default_factory=list)
    detail_rows: list[ProductDetailRow] = Field(default_factory=list)
    gallery_images: list[ProductGalleryImage] = Field(default_factory=list)
    purchase_options: list[ProductPurchaseOption] = Field(default_factory=list)
    stats: ProductStats | None = None
    related_products: list[ProductSummary] = Field(default_factory=list)


class ProductPage(BaseModel):
    items: list[ProductSummary]
    total: int
    limit: int
    offset: int
    discovery: ProductDiscoveryMetadata = Field(default_factory=ProductDiscoveryMetadata)


class ProductCreate(BaseModel):
    category_id: UUID
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    brand: str | None = Field(default=None, max_length=255)
    description: str | None = None
    image_url: str | None = None
    feature_bullets: list[str] = Field(default_factory=list)
    detail_rows: list[ProductDetailRow] = Field(default_factory=list)
    gallery_images: list[ProductGalleryImage] = Field(default_factory=list)
    lowest_ask_cents: int | None = Field(default=None, ge=0)
    total_sold: int = Field(default=0, ge=0)

    @field_validator("feature_bullets", mode="before")
    @classmethod
    def normalize_feature_bullets(cls, value: list[str] | None) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("Feature bullets must be a list.")
        return [text for item in value if (text := str(item).strip())]


class ProductUpdate(BaseModel):
    category_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    brand: str | None = Field(default=None, max_length=255)
    description: str | None = None
    image_url: str | None = None
    feature_bullets: list[str] | None = None
    detail_rows: list[ProductDetailRow] | None = None
    gallery_images: list[ProductGalleryImage] | None = None
    lowest_ask_cents: int | None = Field(default=None, ge=0)
    total_sold: int | None = Field(default=None, ge=0)

    @field_validator("feature_bullets", mode="before")
    @classmethod
    def normalize_optional_feature_bullets(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError("Feature bullets must be a list.")
        return [text for item in value if (text := str(item).strip())]

    @model_validator(mode="after")
    def require_update(self) -> "ProductUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one product field must be provided.")
        for field in ("category_id", "name", "slug", "total_sold"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class AdminProductRead(ProductDetail):
    archived_at: datetime | None = None
    archived_by_user_id: UUID | None = None
    inventory_summary: "AdminProductInventorySummary"
    inventory_items: list["AdminProductInventoryItem"] = Field(default_factory=list)


class AdminProductInventorySummary(BaseModel):
    total_listings: int
    active_listings: int
    total_available_quantity: int
    lowest_active_price_cents: int | None = None


class AdminProductInventoryItem(BaseModel):
    id: UUID
    user_id: UUID
    product_variant_id: UUID | None = None
    variant: ProductVariantRead | None = None
    price_cents: int
    available_quantity: int
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminProductPage(BaseModel):
    items: list[AdminProductRead]
    total: int
    limit: int
    offset: int
