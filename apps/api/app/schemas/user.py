from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserPublic(BaseModel):
    id: UUID
    name: str
    email: str
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

