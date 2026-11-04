from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserPublic(BaseModel):
    id: UUID
    name: str
    email: str
    is_admin: bool
    is_supreme_admin: bool
    is_seller: bool
    is_verified: bool
    verified_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
