from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CategoryRead(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

