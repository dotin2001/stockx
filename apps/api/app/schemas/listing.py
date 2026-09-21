from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductSummary


class ListingCreate(BaseModel):
    product_id: UUID
    product_variant_id: UUID | None = None
    price_cents: int = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class ListingRead(BaseModel):
    id: UUID
    user_id: UUID
    product_id: UUID
    product_variant_id: UUID | None = None
    price_cents: int
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ListingManagementRead(ListingRead):
    product: ProductSummary


class ListingPage(BaseModel):
    items: list[ListingManagementRead]
    total: int
    limit: int
    offset: int
