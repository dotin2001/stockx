from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.customer_message import CustomerMessageCreate, CustomerMessagePage, CustomerMessageRead
from app.services import customer_messages

router = APIRouter()


@router.get("", response_model=CustomerMessagePage)
def list_my_messages(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> CustomerMessagePage:
    messages, total = customer_messages.list_customer_messages(db, user=current_user, limit=limit, offset=offset)
    return CustomerMessagePage(
        items=[customer_messages.serialize_message(message) for message in messages],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=CustomerMessageRead, status_code=status.HTTP_201_CREATED)
def create_message(payload: CustomerMessageCreate, current_user: CurrentUser, db: DbSession) -> CustomerMessageRead:
    message = customer_messages.create_message(db, sender=current_user, payload=payload)
    db.commit()
    return customer_messages.serialize_message(message)


@router.get("/{message_id}", response_model=CustomerMessageRead)
def get_my_message(message_id: UUID, current_user: CurrentUser, db: DbSession) -> CustomerMessageRead:
    message = customer_messages.get_customer_message(db, user=current_user, message_id=message_id)
    return customer_messages.serialize_message(message)
