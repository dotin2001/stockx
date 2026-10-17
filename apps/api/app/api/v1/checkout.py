from typing import Annotated

from fastapi import APIRouter, Header, status

from app.api.deps import CheckoutProvider, CurrentUser, DbSession
from app.api.errors import APIError
from app.schemas.order import CheckoutSummary, PaymentSessionCreateRequest, PaymentSessionRead
from app.services import checkout as checkout_service
from app.services import payment_checkout

router = APIRouter()


@router.get("/summary", response_model=CheckoutSummary)
def get_checkout_summary(current_user: CurrentUser, db: DbSession) -> CheckoutSummary:
    return checkout_service.get_checkout_summary(db, user=current_user)


@router.post("/sessions", response_model=PaymentSessionRead, status_code=status.HTTP_201_CREATED)
def create_checkout_session(
    payload: PaymentSessionCreateRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=255)],
    current_user: CurrentUser,
    db: DbSession,
    provider: CheckoutProvider,
) -> PaymentSessionRead:
    if provider is None:
        raise APIError(
            status.HTTP_409_CONFLICT,
            "stripe_checkout_disabled",
            "Stripe checkout is not enabled.",
        )
    return payment_checkout.start_checkout_session(
        db,
        user=current_user,
        payload=payload,
        idempotency_key=idempotency_key.strip(),
        provider=provider,
    )
