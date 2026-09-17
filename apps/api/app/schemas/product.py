from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.category import CategoryRead


class ProductVariantRead(BaseModel):
    id: UUID
    size: str | None = None
    color: str | None = None
    sku: str | None = None

    model_config = ConfigDict(from_attributes=True)


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


class ProductPage(BaseModel):
    items: list[ProductSummary]
    total: int
    limit: int
    offset: int
