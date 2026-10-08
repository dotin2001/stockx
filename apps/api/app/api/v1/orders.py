from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.schemas.order import OrderCreateRequest, OrderPage, OrderRead
from app.services import orders as order_service
from app.services.integrity import matches_integrity_target

router = APIRouter()

IDEMPOTENCY_UNIQUE_TARGETS = (
    "uq_orders_user_id_idempotency_key",
    "orders.user_id, orders.idempotency_key",
)

IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)]


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreateRequest,
    idempotency_key: IdempotencyKey,
    current_user: CurrentUser,
    db: DbSession,
) -> OrderRead:
    try:
        order = order_service.create_order(
            db,
            user=current_user,
            payload=payload,
            idempotency_key=idempotency_key.strip(),
        )
        db.commit()
        return order
    except IntegrityError as exc:
        db.rollback()
        if not matches_integrity_target(exc, IDEMPOTENCY_UNIQUE_TARGETS):
            raise
        replay = order_service.get_idempotent_replay(
            db,
            user=current_user,
            payload=payload,
            idempotency_key=idempotency_key.strip(),
        )
        if replay is None:
            raise
        db.commit()
        return replay
    except Exception:
        db.rollback()
        raise


@router.get("", response_model=OrderPage)
def list_orders(
    current_user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OrderPage:
    return order_service.list_orders(db, user=current_user, limit=limit, offset=offset)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(order_id: UUID, current_user: CurrentUser, db: DbSession) -> OrderRead:
    return order_service.get_order(db, user=current_user, order_id=order_id)
