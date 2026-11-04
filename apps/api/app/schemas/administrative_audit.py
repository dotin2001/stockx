from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AdministrativeAuditRead(BaseModel):
    id: UUID
    actor_user_id: UUID
    action: str
    target_type: str
    target_id: UUID
    request_id: str
    facts: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdministrativeAuditPage(BaseModel):
    items: list[AdministrativeAuditRead]
    total: int
    limit: int
    offset: int
