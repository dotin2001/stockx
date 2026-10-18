from __future__ import annotations

from uuid import UUID

from fastapi import status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.models import Order, PaymentAttempt
from app.schemas.order import (
    AdminOrderPage,
    AdminOrderSummary,
    OrderRead,
    OrderStatus,
    PaymentAttemptSummary,
    PaymentStatus,
)
from app.services import orders as order_service


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _latest_attempt(order: Order) -> PaymentAttempt | None:
    if not order.payment_attempts:
        return None
    return max(order.payment_attempts, key=lambda attempt: (attempt.created_at, attempt.id))


def serialize_order_summary(order: Order) -> AdminOrderSummary:
    latest_attempt = _latest_attempt(order)
    return AdminOrderSummary(
        id=order.id,
        order_number=order.order_number,
        customer_name=order.customer_name,
        customer_email=order.customer_email,
        status=order.status,
        payment_status=order.payment_status,
        currency=order.currency,
        total_cents=order.total_cents,
        item_line_count=len(order.items),
        item_quantity=sum(item.quantity for item in order.items),
        latest_payment_attempt=(
            PaymentAttemptSummary.model_validate(latest_attempt) if latest_attempt is not None else None
        ),
        confirmed_at=order.confirmed_at,
        created_at=order.created_at,
    )


def list_orders(
    db: Session,
    *,
    search: str | None,
    order_status: OrderStatus | None,
    payment_status: PaymentStatus | None,
    limit: int,
    offset: int,
) -> AdminOrderPage:
    conditions = []
    normalized_search = search.strip() if search else ""
    if normalized_search:
        pattern = f"%{_escape_like(normalized_search)}%"
        conditions.append(
            or_(
                Order.order_number.ilike(pattern, escape="\\"),
                Order.customer_email.ilike(pattern, escape="\\"),
            )
        )
    if order_status is not None:
        conditions.append(Order.status == order_status.value)
    if payment_status is not None:
        conditions.append(Order.payment_status == payment_status.value)

    total_statement = select(func.count()).select_from(Order)
    page_statement = select(Order).options(*order_service.ORDER_LOAD_OPTIONS)
    if conditions:
        total_statement = total_statement.where(*conditions)
        page_statement = page_statement.where(*conditions)

    total = db.scalar(total_statement) or 0
    orders = list(
        db.scalars(
            page_statement.order_by(Order.created_at.desc(), Order.id.desc()).limit(limit).offset(offset)
        ).all()
    )
    return AdminOrderPage(
        items=[serialize_order_summary(order) for order in orders],
        total=total,
        limit=limit,
        offset=offset,
    )


def get_order(db: Session, *, order_id: UUID) -> OrderRead:
    order = db.scalar(
        select(Order).where(Order.id == order_id).options(*order_service.ORDER_LOAD_OPTIONS)
    )
    if order is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "order_not_found", "Order was not found.")
    return order_service.serialize_order(order)
