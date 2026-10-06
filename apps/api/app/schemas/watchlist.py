from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.product import ProductSummary


class WatchlistAdd(BaseModel):
    product_id: UUID


class WatchlistItemRead(BaseModel):
    id: UUID
    product: ProductSummary
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

