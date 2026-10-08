from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.order import CheckoutSummary
from app.services import checkout as checkout_service

router = APIRouter()


@router.get("/summary", response_model=CheckoutSummary)
def get_checkout_summary(current_user: CurrentUser, db: DbSession) -> CheckoutSummary:
    return checkout_service.get_checkout_summary(db, user=current_user)
