from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductSummary


class CartItemAdd(BaseModel):
    listing_id: UUID
    quantity: int = Field(default=1, gt=0)


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0)


class CartListingRead(BaseModel):
    id: UUID
    price_cents: int
    currency: str
    status: str
    product: ProductSummary

    model_config = ConfigDict(from_attributes=True)


class CartItemRead(BaseModel):
    id: UUID
    listing_id: UUID
    quantity: int
    available: bool
    unavailable_reason: str | None = None
    listing: CartListingRead
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CartRead(BaseModel):
    items: list[CartItemRead]
    total_quantity: int
