from typing import Annotated

from fastapi import APIRouter, Header, Request

from app.api.deps import DbSession
from app.services import stripe_webhooks

router = APIRouter()


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    db: DbSession,
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None,
) -> dict[str, bool]:
    payload = await request.body()
    event = stripe_webhooks.verify_event(payload, stripe_signature)
    return stripe_webhooks.handle_verified_event(db, event=event, payload=payload)
