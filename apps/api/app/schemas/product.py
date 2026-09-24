from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.category import CategoryRead


class ProductVariantRead(BaseModel):
    id: UUID
    size: str | None = None
    color: str | None = None
    sku: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ActiveListingSummary(BaseModel):
    id: UUID
    price_cents: int
    currency: str
    status: str
    product_variant_id: UUID | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
    total_sold: int
    category: CategoryRead
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductDetail(ProductSummary):
    description: str | None = None
    variants: list[ProductVariantRead] = Field(default_factory=list)
    lowest_active_listing: ActiveListingSummary | None = None


class ProductPage(BaseModel):
    items: list[ProductSummary]
    total: int
    limit: int
    offset: int


class ProductCreate(BaseModel):
    category_id: UUID
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    brand: str | None = Field(default=None, max_length=255)
    description: str | None = None
    image_url: str | None = None
    lowest_ask_cents: int | None = Field(default=None, ge=0)
    total_sold: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    category_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    brand: str | None = Field(default=None, max_length=255)
    description: str | None = None
    image_url: str | None = None
    lowest_ask_cents: int | None = Field(default=None, ge=0)
    total_sold: int | None = Field(default=None, ge=0)

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


class AdminProductPage(BaseModel):
    items: list[AdminProductRead]
    total: int
    limit: int
    offset: int
