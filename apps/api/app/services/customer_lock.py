from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


def lock_customer_row(db: Session, user_id: UUID) -> User:
    """Serialize account-cart mutations and checkout for one customer."""
    return db.scalars(select(User).where(User.id == user_id).with_for_update()).one()
