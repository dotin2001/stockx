from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AdminUserRead(BaseModel):
    id: UUID
    name: str
    email: str
    is_admin: bool
    is_supreme_admin: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminUserPage(BaseModel):
    items: list[AdminUserRead]
    total: int
    limit: int
    offset: int


class AdminUserPromoteByEmail(BaseModel):
    email: str = Field(min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value:
            raise ValueError("Email must be valid.")
        return value
