from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.errors import APIError
from app.models import CustomerAdminMessage, User
from app.schemas.customer_message import CustomerMessageCreate, CustomerMessageRead


MESSAGE_LOAD_OPTIONS = (selectinload(CustomerAdminMessage.sender),)


def serialize_message(message: CustomerAdminMessage) -> CustomerMessageRead:
    return CustomerMessageRead(
        id=message.id,
        sender_user_id=message.sender_user_id,
        sender_name=message.sender.name,
        sender_email=message.sender.email,
        subject=message.subject,
        body=message.body,
        is_read=message.is_read,
        read_at=message.read_at,
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


def create_message(db: Session, *, sender: User, payload: CustomerMessageCreate) -> CustomerAdminMessage:
    if sender.is_admin:
        raise APIError(status.HTTP_403_FORBIDDEN, "customer_required", "Customer messages must be sent from a customer account.")

    message = CustomerAdminMessage(sender_user_id=sender.id, subject=payload.subject, body=payload.body)
    db.add(message)
    db.flush()
    return get_customer_message(db, user=sender, message_id=message.id)


def list_customer_messages(db: Session, *, user: User, limit: int, offset: int) -> tuple[list[CustomerAdminMessage], int]:
    criteria = (CustomerAdminMessage.sender_user_id == user.id,)
    total = db.scalar(select(func.count()).select_from(CustomerAdminMessage).where(*criteria)) or 0
    messages = list(
        db.scalars(
            select(CustomerAdminMessage)
            .where(*criteria)
            .options(*MESSAGE_LOAD_OPTIONS)
            .order_by(CustomerAdminMessage.created_at.desc(), CustomerAdminMessage.id)
            .limit(limit)
            .offset(offset)
            .execution_options(populate_existing=True)
        ).all()
    )
    return messages, total


def get_customer_message(db: Session, *, user: User, message_id: UUID) -> CustomerAdminMessage:
    message = db.scalar(
        select(CustomerAdminMessage)
        .where(CustomerAdminMessage.id == message_id, CustomerAdminMessage.sender_user_id == user.id)
        .options(*MESSAGE_LOAD_OPTIONS)
        .execution_options(populate_existing=True)
    )
    if message is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "message_not_found", "Message was not found.")
    return message


def list_admin_messages(db: Session, *, limit: int, offset: int) -> tuple[list[CustomerAdminMessage], int]:
    total = db.scalar(select(func.count()).select_from(CustomerAdminMessage)) or 0
    messages = list(
        db.scalars(
            select(CustomerAdminMessage)
            .options(*MESSAGE_LOAD_OPTIONS)
            .order_by(CustomerAdminMessage.is_read, CustomerAdminMessage.created_at.desc(), CustomerAdminMessage.id)
            .limit(limit)
            .offset(offset)
            .execution_options(populate_existing=True)
        ).all()
    )
    return messages, total


def get_admin_message(db: Session, *, message_id: UUID) -> CustomerAdminMessage:
    message = db.scalar(
        select(CustomerAdminMessage)
        .where(CustomerAdminMessage.id == message_id)
        .options(*MESSAGE_LOAD_OPTIONS)
        .execution_options(populate_existing=True)
    )
    if message is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "message_not_found", "Message was not found.")
    return message


def mark_admin_message_read(db: Session, *, message_id: UUID) -> CustomerAdminMessage:
    message = get_admin_message(db, message_id=message_id)
    if not message.is_read:
        message.is_read = True
        message.read_at = datetime.now(UTC)
    db.flush()
    return get_admin_message(db, message_id=message.id)
