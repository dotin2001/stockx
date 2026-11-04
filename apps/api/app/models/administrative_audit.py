from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AdministrativeAudit(Base):
    __tablename__ = "administrative_audits"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    actor_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[UUID] = mapped_column(nullable=False)
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    facts: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    actor = relationship("User", foreign_keys=[actor_user_id])

    __table_args__ = (
        CheckConstraint("trim(action) <> ''", name="action_not_blank"),
        CheckConstraint("trim(target_type) <> ''", name="target_type_not_blank"),
        CheckConstraint("trim(request_id) <> ''", name="request_id_not_blank"),
        CheckConstraint("length(CAST(facts AS TEXT)) <= 16384", name="facts_bounded"),
        Index("ix_administrative_audits_created_id", "created_at", "id"),
        Index("ix_administrative_audits_actor_created", "actor_user_id", "created_at"),
        Index("ix_administrative_audits_action_created", "action", "created_at"),
        Index("ix_administrative_audits_target_created", "target_type", "target_id", "created_at"),
    )
