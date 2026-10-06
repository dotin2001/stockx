from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SellerProfileUpsert(BaseModel):
    phone_number: str = Field(min_length=3, max_length=32)
    address_line1: str = Field(min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=128)
    state: str | None = Field(default=None, max_length=128)
    postal_code: str | None = Field(default=None, max_length=32)
    country: str = Field(min_length=2, max_length=2)

    @field_validator("phone_number", "address_line1", "city", "country")
    @classmethod
    def strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field is required.")
        return value

    @field_validator("address_line2", "state", "postal_code")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator("country")
    @classmethod
    def normalize_country(cls, value: str) -> str:
        return value.upper()


class SellerProfileRead(BaseModel):
    id: UUID
    user_id: UUID
    phone_number: str
    address_line1: str
    address_line2: str | None = None
    city: str
    state: str | None = None
    postal_code: str | None = None
    country: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
