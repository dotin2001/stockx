from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CustomerMessageCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=4000)

    @field_validator("subject", "body")
    @classmethod
    def strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field is required.")
        return value


class CustomerMessageRead(BaseModel):
    id: UUID
    sender_user_id: UUID
    sender_name: str
    sender_email: str
    subject: str
    body: str
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerMessagePage(BaseModel):
    items: list[CustomerMessageRead]
    total: int
    limit: int
    offset: int
