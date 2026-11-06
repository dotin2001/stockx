from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AdministrativeAudit, User
from app.services.observability import current_request_id


ALLOWED_FACT_KEYS = {
    "is_admin",
    "is_read",
    "archived",
    "available_quantity",
    "reserved_quantity",
    "status",
    "price_cents",
    "currency",
    "category_id",
    "product_variant_id",
    "name",
    "slug",
    "brand",
    "sku",
    "size",
    "color",
}
MAX_FACT_STRING_LENGTH = 256


def write_audit(
    db: Session,
    *,
    actor: User,
    action: str,
    target_type: str,
    target_id: UUID,
    request_id: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
) -> AdministrativeAudit:
    def allow(values: dict | None) -> dict:
        safe: dict[str, str | int | float | bool | None] = {}
        for key in sorted(values or {}):
            value = values[key]
            if key not in ALLOWED_FACT_KEYS or value is not None and not isinstance(value, (str, int, float, bool)):
                continue
            safe[key] = value[:MAX_FACT_STRING_LENGTH] if isinstance(value, str) else value
        return safe

    record = AdministrativeAudit(
        actor_user_id=actor.id,
        action=action[:80],
        target_type=target_type[:64],
        target_id=target_id,
        request_id=(request_id or current_request_id())[:64],
        facts={"before": allow(before), "after": allow(after)},
    )
    db.add(record)
    db.flush()
    return record


def list_audits(
    db: Session,
    *,
    actor_user_id: UUID | None,
    action: str | None,
    target_type: str | None,
    target_id: UUID | None,
    created_from: datetime | None,
    created_to: datetime | None,
    limit: int,
    offset: int,
) -> tuple[list[AdministrativeAudit], int]:
    criteria = []
    if actor_user_id is not None:
        criteria.append(AdministrativeAudit.actor_user_id == actor_user_id)
    if action is not None:
        criteria.append(AdministrativeAudit.action == action)
    if target_type is not None:
        criteria.append(AdministrativeAudit.target_type == target_type)
    if target_id is not None:
        criteria.append(AdministrativeAudit.target_id == target_id)
    if created_from is not None:
        criteria.append(AdministrativeAudit.created_at >= created_from)
    if created_to is not None:
        criteria.append(AdministrativeAudit.created_at <= created_to)
    count = select(func.count()).select_from(AdministrativeAudit).where(*criteria)
    query = (
        select(AdministrativeAudit)
        .where(*criteria)
        .order_by(AdministrativeAudit.created_at.desc(), AdministrativeAudit.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(query).all()), db.scalar(count) or 0
