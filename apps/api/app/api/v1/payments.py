from typing import Annotated

from fastapi import APIRouter, Header, Request

from app.api.deps import DbSession
from app.api.errors import APIError
from app.services import stripe_webhooks

router = APIRouter()


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    db: DbSession,
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None,
) -> dict[str, bool]:
    payload = await request.body()
    try:
        event = stripe_webhooks.verify_event(payload, stripe_signature)
    except APIError as exc:
        stripe_webhooks.record_verification_failure(
            db,
            payload=payload,
            category="verification_failed",
        )
        raise exc
    return stripe_webhooks.handle_verified_event(db, event=event, payload=payload)
