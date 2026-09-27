from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.product import ProductSummary


class ListingCreate(BaseModel):
    product_id: UUID
    product_variant_id: UUID | None = None
    price_cents: int = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class AdminListingCreate(BaseModel):
    product_variant_id: UUID | None = None
    price_cents: int = Field(gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    available_quantity: int = Field(ge=0)
    status: str = Field(default="active", pattern="^(active|sold|cancelled)$")

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class ListingRead(BaseModel):
    id: UUID
    user_id: UUID
    product_id: UUID
    product_variant_id: UUID | None = None
    price_cents: int
    available_quantity: int
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ListingManagementRead(ListingRead):
    product: ProductSummary


class ListingQuantityAdjustment(BaseModel):
    adjustment: int

    @model_validator(mode="after")
    def require_non_zero_adjustment(self) -> "ListingQuantityAdjustment":
        if self.adjustment == 0:
            raise ValueError("adjustment must be non-zero.")
        return self


class ListingStatusUpdate(BaseModel):
    status: str = Field(pattern="^(active|sold|cancelled)$")


class ListingPage(BaseModel):
    items: list[ListingManagementRead]
    total: int
    limit: int
    offset: int
