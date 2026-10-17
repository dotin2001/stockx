from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

import stripe
from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.core.config import settings
from app.models import Order, PaymentAttempt, StripeWebhookEvent
from app.payments import CheckoutSessionProvider, PaymentProviderError, ProviderCheckoutSession
from app.services import payment_checkout
from app.services.customer_lock import lock_customer_row


SUPPORTED_EVENT_TYPES = {
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
    "checkout.session.async_payment_failed",
    "checkout.session.expired",
}


def verify_event(payload: bytes, signature: str | None) -> dict[str, Any]:
    if not signature:
        raise APIError(status.HTTP_400_BAD_REQUEST, "invalid_stripe_signature", "Stripe signature is required.")
    if settings.stripe_webhook_secret is None:
        raise APIError(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "stripe_configuration_error",
            "Stripe webhook verification is not configured.",
        )
    try:
        event = stripe.Webhook.construct_event(
            payload,
            signature,
            settings.stripe_webhook_secret.get_secret_value(),
            tolerance=300,
        )
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise APIError(status.HTTP_400_BAD_REQUEST, "invalid_stripe_signature", "Stripe signature is invalid.") from exc
    if hasattr(event, "to_dict_recursive"):
        return event.to_dict_recursive()
    if hasattr(event, "to_dict"):
        return event.to_dict()
    return dict(event)


def _event_object(event: dict[str, Any]) -> dict[str, Any]:
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    return data.get("object") if isinstance(data.get("object"), dict) else {}


def _resource_id(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and value.get("id"):
        return str(value["id"])
    return None


def _integer_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _fail_event(db: Session, record: StripeWebhookEvent, code: str) -> None:
    record.processing_status = "failed"
    record.error_summary = code[:255]
    record.processed_at = datetime.now(UTC)
    db.commit()


def _correlated_session(
    db: Session,
    *,
    record: StripeWebhookEvent,
    event: dict[str, Any],
    provider_object: dict[str, Any],
) -> tuple[PaymentAttempt, Order, ProviderCheckoutSession] | None:
    session_id = str(provider_object.get("id", ""))
    initial_attempt = db.scalar(
        select(PaymentAttempt).where(PaymentAttempt.provider_session_id == session_id)
    )
    if initial_attempt is None:
        _fail_event(db, record, "unknown_checkout_session")
        return None
    initial_order = db.get(Order, initial_attempt.order_id)
    if initial_order is None:
        _fail_event(db, record, "missing_order")
        return None

    lock_customer_row(db, initial_order.user_id)
    order = db.scalar(select(Order).where(Order.id == initial_order.id).with_for_update())
    attempt = db.scalar(select(PaymentAttempt).where(PaymentAttempt.id == initial_attempt.id).with_for_update())
    if order is None or attempt is None:
        _fail_event(db, record, "missing_correlated_state")
        return None
    record.payment_attempt_id = attempt.id

    metadata = provider_object.get("metadata") if isinstance(provider_object.get("metadata"), dict) else {}
    expected_metadata = {
        "order_id": str(order.id),
        "payment_attempt_id": str(attempt.id),
        "correlation_id": attempt.correlation_id,
    }
    session_livemode = bool(provider_object.get("livemode", event.get("livemode", False)))
    event_livemode = bool(event.get("livemode", False))
    payment_intent_id = _resource_id(provider_object.get("payment_intent"))
    checks = (
        (record.provider_object_id == attempt.provider_session_id, "session_id_mismatch"),
        (metadata == expected_metadata, "metadata_mismatch"),
        (_integer_value(provider_object.get("amount_total")) == attempt.amount_cents, "amount_mismatch"),
        (str(provider_object.get("currency", "")).upper() == attempt.currency, "currency_mismatch"),
        (
            event_livemode == session_livemode == attempt.provider_livemode == settings.stripe_expected_livemode,
            "livemode_mismatch",
        ),
        (
            attempt.provider_payment_intent_id is None
            or payment_intent_id == attempt.provider_payment_intent_id,
            "payment_intent_mismatch",
        ),
        (attempt.order_id == order.id, "ownership_mismatch"),
    )
    for valid, code in checks:
        if not valid:
            _fail_event(db, record, code)
            return None

    expires_at_value = _integer_value(provider_object.get("expires_at"))
    expires_at = (
        datetime.fromtimestamp(expires_at_value, tz=UTC)
        if expires_at_value is not None
        else attempt.expires_at
    )
    provider_session = ProviderCheckoutSession(
        id=session_id,
        payment_intent_id=payment_intent_id,
        url=provider_object.get("url"),
        status=str(provider_object.get("status", "open")),
        payment_status=str(provider_object.get("payment_status", "unpaid")),
        amount_total_cents=_integer_value(provider_object.get("amount_total")) or 0,
        currency=str(provider_object.get("currency", "")).upper(),
        livemode=session_livemode,
        expires_at=expires_at,
        metadata={str(key): str(value) for key, value in metadata.items()},
    )
    return attempt, order, provider_session


def _apply_event_transition(
    db: Session,
    *,
    record: StripeWebhookEvent,
    event_type: str,
    attempt: PaymentAttempt,
    provider_session: ProviderCheckoutSession,
) -> None:
    if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
        if provider_session.payment_status == "paid":
            payment_checkout.mark_payment_paid(
                db,
                attempt_id=attempt.id,
                provider_session=provider_session,
            )
        elif event_type == "checkout.session.completed":
            payment_checkout.mark_payment_processing(
                db,
                attempt_id=attempt.id,
                provider_session=provider_session,
            )
        else:
            _fail_event(db, record, "async_success_not_paid")
            return
    elif event_type == "checkout.session.async_payment_failed":
        if provider_session.payment_status == "paid":
            payment_checkout.mark_payment_paid(db, attempt_id=attempt.id, provider_session=provider_session)
        else:
            payment_checkout.release_terminal_reservation(
                db,
                attempt_id=attempt.id,
                attempt_status="failed",
                failure_code="async_payment_failed",
            )
    elif event_type == "checkout.session.expired":
        if provider_session.payment_status == "paid":
            payment_checkout.mark_payment_paid(db, attempt_id=attempt.id, provider_session=provider_session)
        else:
            payment_checkout.release_terminal_reservation(
                db,
                attempt_id=attempt.id,
                attempt_status="expired",
                failure_code="session_expired",
            )
    record.processing_status = "processed"
    record.error_summary = None
    record.processed_at = datetime.now(UTC)
    db.commit()


def handle_verified_event(db: Session, *, event: dict[str, Any], payload: bytes) -> dict[str, bool]:
    event_type = str(event.get("type", ""))
    if event_type not in SUPPORTED_EVENT_TYPES:
        return {"received": True}

    digest = hashlib.sha256(payload).hexdigest()
    event_id = str(event.get("id") or f"invalid-{digest[:24]}")
    provider_object = _event_object(event)
    provider_object_id = provider_object.get("id")
    existing = db.scalar(select(StripeWebhookEvent).where(StripeWebhookEvent.stripe_event_id == event_id))
    if existing is not None and existing.processing_status in {"processed", "ignored", "failed"}:
        db.rollback()
        return {"received": True}

    record = existing or StripeWebhookEvent(
        stripe_event_id=event_id,
        event_type=event_type,
        provider_object_id=str(provider_object_id) if provider_object_id else None,
        livemode=bool(event.get("livemode", False)),
        processing_status="received",
        payload_digest=digest,
    )
    if existing is None:
        db.add(record)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            duplicate = db.scalar(select(StripeWebhookEvent).where(StripeWebhookEvent.stripe_event_id == event_id))
            if duplicate is None:
                raise
            return {"received": True}

    if not provider_object_id:
        _fail_event(db, record, "missing_provider_object_id")
        return {"received": True}
    correlated = _correlated_session(db, record=record, event=event, provider_object=provider_object)
    if correlated is None:
        return {"received": True}
    attempt, _order, provider_session = correlated
    try:
        _apply_event_transition(
            db,
            record=record,
            event_type=event_type,
            attempt=attempt,
            provider_session=provider_session,
        )
    except Exception:
        db.rollback()
        raise
    return {"received": True}


def reprocess_stripe_event(
    db: Session,
    *,
    stripe_event_id: str,
    provider: CheckoutSessionProvider,
) -> payment_checkout.ReconciliationOutcome:
    """Reconcile a stored event from the provider's current Checkout Session state."""
    record = db.scalar(
        select(StripeWebhookEvent).where(StripeWebhookEvent.stripe_event_id == stripe_event_id)
    )
    if record is None:
        return payment_checkout.ReconciliationOutcome(stripe_event_id, "missing_event")
    if record.processing_status == "processed":
        return payment_checkout.ReconciliationOutcome(stripe_event_id, "already_processed")
    if not record.provider_object_id:
        _fail_event(db, record, "missing_provider_object_id")
        return payment_checkout.ReconciliationOutcome(stripe_event_id, "failed", "missing_provider_object_id")

    try:
        provider_session = provider.retrieve_session(record.provider_object_id)
    except PaymentProviderError:
        _fail_event(db, record, "provider_retrieval_failed")
        return payment_checkout.ReconciliationOutcome(stripe_event_id, "provider_unavailable")

    provider_object = {
        "id": provider_session.id,
        "object": "checkout.session",
        "payment_intent": provider_session.payment_intent_id,
        "url": provider_session.url,
        "status": provider_session.status,
        "payment_status": provider_session.payment_status,
        "amount_total": provider_session.amount_total_cents,
        "currency": provider_session.currency.lower(),
        "livemode": provider_session.livemode,
        "expires_at": int(provider_session.expires_at.timestamp()),
        "metadata": provider_session.metadata,
    }
    event = {
        "id": record.stripe_event_id,
        "type": record.event_type,
        "livemode": provider_session.livemode,
        "data": {"object": provider_object},
    }
    record.processing_status = "received"
    record.error_summary = None
    correlated = _correlated_session(db, record=record, event=event, provider_object=provider_object)
    if correlated is None:
        return payment_checkout.ReconciliationOutcome(
            stripe_event_id,
            "failed",
            record.error_summary,
        )

    attempt, _order, correlated_session = correlated
    try:
        _apply_event_transition(
            db,
            record=record,
            event_type=record.event_type,
            attempt=attempt,
            provider_session=correlated_session,
        )
    except Exception:
        db.rollback()
        raise
    db.refresh(attempt)
    return payment_checkout.ReconciliationOutcome(str(attempt.id), attempt.status)
