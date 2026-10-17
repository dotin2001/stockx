from __future__ import annotations

import hashlib
import hmac
import json
import time
from copy import deepcopy
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import CheckoutMode, settings
from app.models import CartItem, Listing, Order, PaymentAttempt, StripeWebhookEvent
from app.payments import FakeCheckoutSessionProvider
from app.schemas.order import PaymentSessionCreateRequest
from app.services import checkout, payment_checkout, stripe_webhooks
from tests.test_checkout_orders import create_cart_listing, order_payload, register


WEBHOOK_SECRET = "whsec_test_webhook_secret"


@pytest.fixture(autouse=True)
def stripe_settings():
    previous_mode = settings.checkout_mode
    previous_base_url = settings.frontend_base_url
    previous_livemode = settings.stripe_expected_livemode
    settings.checkout_mode = CheckoutMode.STRIPE
    settings.frontend_base_url = "https://shop.example.com"
    settings.stripe_expected_livemode = False
    try:
        yield
    finally:
        settings.checkout_mode = previous_mode
        settings.frontend_base_url = previous_base_url
        settings.stripe_expected_livemode = previous_livemode


def event_payload(*, event_id: str = "evt_test_signature", event_type: str = "customer.created") -> bytes:
    return json.dumps(
        {
            "id": event_id,
            "object": "event",
            "type": event_type,
            "livemode": False,
            "data": {"object": {"id": "cus_test", "object": "customer"}},
        },
        separators=(",", ":"),
    ).encode()


def signature_for(payload: bytes, *, secret: str = WEBHOOK_SECRET, timestamp: int | None = None) -> str:
    signed_at = int(time.time()) if timestamp is None else timestamp
    signed_payload = f"{signed_at}.".encode() + payload
    digest = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return f"t={signed_at},v1={digest}"


def start_local_payment(
    client: TestClient,
    db_session: Session,
    *,
    email: str,
    quantity: int = 1,
    available_quantity: int = 4,
):
    register(client, email)
    buyer, listing, _cart_item = create_cart_listing(
        db_session,
        buyer_email=email,
        quantity=quantity,
        available_quantity=available_quantity,
    )
    summary = checkout.get_checkout_summary(db_session, user=buyer)
    provider = FakeCheckoutSessionProvider()
    started = payment_checkout.start_checkout_session(
        db_session,
        user=buyer,
        payload=PaymentSessionCreateRequest(
            checkout_token=summary.checkout_token,
            shipping=order_payload(summary.checkout_token)["shipping"],
        ),
        idempotency_key=f"webhook-{uuid4().hex}",
        provider=provider,
    )
    return buyer, listing, provider, started


def checkout_event(
    *,
    event_id: str,
    event_type: str,
    started,
    provider: FakeCheckoutSessionProvider,
    payment_status: str,
    session_status: str,
) -> tuple[dict, bytes]:
    provider_session = provider.retrieve_session(started.provider_session_id)
    event = {
        "id": event_id,
        "object": "event",
        "type": event_type,
        "livemode": provider_session.livemode,
        "data": {
            "object": {
                "id": provider_session.id,
                "object": "checkout.session",
                "payment_intent": "pi_webhook_test" if payment_status == "paid" else None,
                "url": provider_session.url,
                "status": session_status,
                "payment_status": payment_status,
                "amount_total": provider_session.amount_total_cents,
                "currency": provider_session.currency.lower(),
                "livemode": provider_session.livemode,
                "expires_at": int(provider_session.expires_at.timestamp()),
                "metadata": provider_session.metadata,
            }
        },
    }
    return event, json.dumps(event, separators=(",", ":")).encode()


def test_webhook_rejects_missing_invalid_altered_stale_and_wrong_secret_signatures(
    client: TestClient,
    db_session: Session,
) -> None:
    previous = settings.stripe_webhook_secret
    settings.stripe_webhook_secret = SecretStr(WEBHOOK_SECRET)
    payload = event_payload()
    requests = [
        (payload, None),
        (payload, "t=1,v1=invalid"),
        (event_payload(event_id="evt_altered"), signature_for(payload)),
        (payload, signature_for(payload, timestamp=int(time.time()) - 301)),
        (payload, signature_for(payload, secret="whsec_wrong")),
    ]
    try:
        for body, signature in requests:
            headers = {"Content-Type": "application/json"}
            if signature is not None:
                headers["Stripe-Signature"] = signature
            response = client.post("/api/v1/payments/stripe/webhook", content=body, headers=headers)
            assert response.status_code == 400
            assert response.json()["error"]["code"] == "invalid_stripe_signature"
            assert db_session.scalar(select(func.count()).select_from(StripeWebhookEvent)) == 0
            assert db_session.scalar(select(func.count()).select_from(PaymentAttempt)) == 0
            assert db_session.scalar(select(func.count()).select_from(Order)) == 0
    finally:
        settings.stripe_webhook_secret = previous


def test_valid_unsupported_webhook_is_acknowledged_without_persistence(
    client: TestClient,
    db_session: Session,
) -> None:
    previous = settings.stripe_webhook_secret
    settings.stripe_webhook_secret = SecretStr(WEBHOOK_SECRET)
    payload = event_payload(event_type="customer.created")
    try:
        response = client.post(
            "/api/v1/payments/stripe/webhook",
            content=payload,
            headers={"Content-Type": "application/json", "Stripe-Signature": signature_for(payload)},
        )
    finally:
        settings.stripe_webhook_secret = previous
    assert response.status_code == 200
    assert response.json() == {"received": True}
    assert db_session.scalar(select(func.count()).select_from(StripeWebhookEvent)) == 0


def test_supported_events_are_durable_deduplicated_and_store_only_safe_metadata(
    client: TestClient,
    db_session: Session,
) -> None:
    previous = settings.stripe_webhook_secret
    settings.stripe_webhook_secret = SecretStr(WEBHOOK_SECRET)
    payload = json.dumps(
        {
            "id": "evt_supported_once",
            "object": "event",
            "type": "checkout.session.completed",
            "livemode": False,
            "data": {
                "object": {
                    "id": "cs_test_shared_object",
                    "object": "checkout.session",
                    "payment_status": "paid",
                    "customer_details": {"email": "buyer@example.com"},
                    "payment_method_details": {"card": {"last4": "4242"}},
                }
            },
        },
        separators=(",", ":"),
    ).encode()
    try:
        first = client.post(
            "/api/v1/payments/stripe/webhook",
            content=payload,
            headers={"Content-Type": "application/json", "Stripe-Signature": signature_for(payload)},
        )
        replay = client.post(
            "/api/v1/payments/stripe/webhook",
            content=payload,
            headers={"Content-Type": "application/json", "Stripe-Signature": signature_for(payload)},
        )
        distinct = event_payload(
            event_id="evt_supported_distinct",
            event_type="checkout.session.async_payment_succeeded",
        ).replace(b"cus_test", b"cs_test_shared_object")
        second = client.post(
            "/api/v1/payments/stripe/webhook",
            content=distinct,
            headers={"Content-Type": "application/json", "Stripe-Signature": signature_for(distinct)},
        )
    finally:
        settings.stripe_webhook_secret = previous

    assert first.status_code == replay.status_code == second.status_code == 200
    records = list(db_session.scalars(select(StripeWebhookEvent).order_by(StripeWebhookEvent.stripe_event_id)).all())
    assert len(records) == 2
    assert {record.provider_object_id for record in records} == {"cs_test_shared_object"}
    assert all(len(record.payload_digest) == 64 for record in records)
    assert all(record.processing_status == "failed" for record in records)
    assert all(record.error_summary == "unknown_checkout_session" for record in records)
    assert {"payload", "raw_payload", "card", "card_data"}.isdisjoint(StripeWebhookEvent.__table__.c.keys())
    assert "4242" not in " ".join(filter(None, (record.error_summary for record in records)))


def test_webhook_correlation_mismatches_are_audited_without_business_mutation(
    client: TestClient,
    db_session: Session,
) -> None:
    _buyer, listing, provider, started = start_local_payment(
        client,
        db_session,
        email="webhook-mismatch@example.com",
        quantity=1,
        available_quantity=3,
    )
    base_event, _ = checkout_event(
        event_id="evt_mismatch_base",
        event_type="checkout.session.completed",
        started=started,
        provider=provider,
        payment_status="paid",
        session_status="complete",
    )
    attempt = db_session.get(PaymentAttempt, started.payment_attempt_id)
    assert attempt is not None
    attempt.provider_payment_intent_id = "pi_expected"
    db_session.commit()

    mutations = [
        ("amount_mismatch", lambda obj: obj.update(amount_total=obj["amount_total"] + 1)),
        ("currency_mismatch", lambda obj: obj.update(currency="eur")),
        ("livemode_mismatch", lambda obj: obj.update(livemode=True)),
        ("metadata_mismatch", lambda obj: obj.update(metadata={**obj["metadata"], "order_id": str(UUID(int=0))})),
        ("payment_intent_mismatch", lambda obj: obj.update(payment_intent="pi_wrong")),
    ]
    for index, (expected_code, mutate) in enumerate(mutations):
        event = deepcopy(base_event)
        event["id"] = f"evt_mismatch_{index}"
        mutate(event["data"]["object"])
        if expected_code == "livemode_mismatch":
            event["livemode"] = True
        payload = json.dumps(event, separators=(",", ":")).encode()
        assert stripe_webhooks.handle_verified_event(db_session, event=event, payload=payload) == {"received": True}
        record = db_session.scalar(
            select(StripeWebhookEvent).where(StripeWebhookEvent.stripe_event_id == event["id"])
        )
        assert record is not None and record.processing_status == "failed"
        assert record.error_summary == expected_code

    unknown = deepcopy(base_event)
    unknown["id"] = "evt_unknown_session"
    unknown["data"]["object"]["id"] = "cs_test_unknown"
    payload = json.dumps(unknown, separators=(",", ":")).encode()
    stripe_webhooks.handle_verified_event(db_session, event=unknown, payload=payload)
    unknown_record = db_session.scalar(
        select(StripeWebhookEvent).where(StripeWebhookEvent.stripe_event_id == "evt_unknown_session")
    )
    assert unknown_record is not None and unknown_record.error_summary == "unknown_checkout_session"

    order = db_session.get(Order, started.order_id)
    db_session.refresh(listing)
    assert order is not None and order.status == "pending_payment" and order.payment_status == "unpaid"
    assert attempt.status == "open"
    assert listing.available_quantity == 2


def test_completed_and_async_success_transitions_are_monotonic_and_do_not_decrement_twice(
    client: TestClient,
    db_session: Session,
) -> None:
    _buyer, listing, provider, started = start_local_payment(
        client,
        db_session,
        email="webhook-success@example.com",
        quantity=1,
        available_quantity=3,
    )
    completed, completed_payload = checkout_event(
        event_id="evt_completed_processing",
        event_type="checkout.session.completed",
        started=started,
        provider=provider,
        payment_status="unpaid",
        session_status="complete",
    )
    stripe_webhooks.handle_verified_event(db_session, event=completed, payload=completed_payload)
    attempt = db_session.get(PaymentAttempt, started.payment_attempt_id)
    order = db_session.get(Order, started.order_id)
    assert attempt is not None and attempt.status == "processing"
    assert order is not None and order.status == "pending_payment" and order.payment_status == "unpaid"

    succeeded, succeeded_payload = checkout_event(
        event_id="evt_async_success",
        event_type="checkout.session.async_payment_succeeded",
        started=started,
        provider=provider,
        payment_status="paid",
        session_status="complete",
    )
    stripe_webhooks.handle_verified_event(db_session, event=succeeded, payload=succeeded_payload)
    distinct = deepcopy(succeeded)
    distinct["id"] = "evt_async_success_distinct"
    distinct_payload = json.dumps(distinct, separators=(",", ":")).encode()
    stripe_webhooks.handle_verified_event(db_session, event=distinct, payload=distinct_payload)
    stripe_webhooks.handle_verified_event(db_session, event=succeeded, payload=succeeded_payload)

    db_session.refresh(attempt)
    db_session.refresh(order)
    db_session.refresh(listing)
    assert attempt.status == "paid" and attempt.completed_at is not None
    assert order.status == "confirmed" and order.payment_status == "paid" and order.confirmed_at is not None
    assert order.inventory_released_at is None
    assert listing.available_quantity == 2


def test_terminal_failure_and_expiry_release_inventory_once_and_never_override_paid(
    client: TestClient,
    db_session: Session,
) -> None:
    buyer, listing, provider, started = start_local_payment(
        client,
        db_session,
        email="webhook-terminal@example.com",
        quantity=1,
        available_quantity=4,
    )
    failed, failed_payload = checkout_event(
        event_id="evt_async_failed",
        event_type="checkout.session.async_payment_failed",
        started=started,
        provider=provider,
        payment_status="unpaid",
        session_status="complete",
    )
    stripe_webhooks.handle_verified_event(db_session, event=failed, payload=failed_payload)
    replay = deepcopy(failed)
    replay["id"] = "evt_async_failed_distinct"
    replay_payload = json.dumps(replay, separators=(",", ":")).encode()
    stripe_webhooks.handle_verified_event(db_session, event=replay, payload=replay_payload)
    stripe_webhooks.handle_verified_event(db_session, event=failed, payload=failed_payload)
    db_session.refresh(listing)
    first_order = db_session.get(Order, started.order_id)
    assert first_order is not None and first_order.status == "cancelled"
    assert first_order.inventory_released_at is not None
    assert listing.available_quantity == 4

    db_session.add(CartItem(user_id=buyer.id, listing_id=listing.id, quantity=1))
    db_session.commit()
    paid_started = payment_checkout.start_checkout_session(
        db_session,
        user=buyer,
        payload=PaymentSessionCreateRequest(
            checkout_token=checkout.get_checkout_summary(db_session, user=buyer).checkout_token,
            shipping=order_payload("unused")["shipping"],
        ),
        idempotency_key="paid-before-failure",
        provider=provider,
    )
    paid_event, paid_payload = checkout_event(
        event_id="evt_paid_before_failure",
        event_type="checkout.session.completed",
        started=paid_started,
        provider=provider,
        payment_status="paid",
        session_status="complete",
    )
    stripe_webhooks.handle_verified_event(db_session, event=paid_event, payload=paid_payload)
    late_failure = deepcopy(paid_event)
    late_failure["id"] = "evt_late_failure"
    late_failure["type"] = "checkout.session.expired"
    late_failure["data"]["object"]["payment_status"] = "unpaid"
    late_failure["data"]["object"]["status"] = "expired"
    late_failure_payload = json.dumps(late_failure, separators=(",", ":")).encode()
    stripe_webhooks.handle_verified_event(db_session, event=late_failure, payload=late_failure_payload)
    paid_order = db_session.get(Order, paid_started.order_id)
    db_session.refresh(listing)
    assert paid_order is not None and paid_order.status == "confirmed" and paid_order.payment_status == "paid"
    assert paid_order.inventory_released_at is None
    assert listing.available_quantity == 3


def test_expired_webhook_closes_reservation_when_source_listing_was_deleted(
    client: TestClient,
    db_session: Session,
) -> None:
    _buyer, listing, provider, started = start_local_payment(
        client,
        db_session,
        email="webhook-missing-listing@example.com",
        quantity=1,
        available_quantity=2,
    )
    listing_id = listing.id
    db_session.delete(listing)
    db_session.commit()

    expired, expired_payload = checkout_event(
        event_id="evt_expired_missing_listing",
        event_type="checkout.session.expired",
        started=started,
        provider=provider,
        payment_status="unpaid",
        session_status="expired",
    )
    stripe_webhooks.handle_verified_event(db_session, event=expired, payload=expired_payload)

    order = db_session.get(Order, started.order_id)
    attempt = db_session.get(PaymentAttempt, started.payment_attempt_id)
    record = db_session.scalar(
        select(StripeWebhookEvent).where(
            StripeWebhookEvent.stripe_event_id == "evt_expired_missing_listing"
        )
    )
    assert db_session.get(Listing, listing_id) is None
    assert order is not None and order.status == "cancelled" and order.payment_status == "failed"
    assert order.inventory_released_at is not None
    assert attempt is not None and attempt.status == "expired"
    assert record is not None and record.processing_status == "processed"


def test_terminal_webhook_commit_failure_rolls_back_event_and_inventory_release(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _buyer, listing, provider, started = start_local_payment(
        client,
        db_session,
        email="webhook-rollback@example.com",
        quantity=1,
        available_quantity=3,
    )
    failed, failed_payload = checkout_event(
        event_id="evt_terminal_rollback",
        event_type="checkout.session.async_payment_failed",
        started=started,
        provider=provider,
        payment_status="unpaid",
        session_status="complete",
    )

    with monkeypatch.context() as scoped_patch:
        scoped_patch.setattr(db_session, "commit", lambda: (_ for _ in ()).throw(RuntimeError("forced commit failure")))
        with pytest.raises(RuntimeError, match="forced commit failure"):
            stripe_webhooks.handle_verified_event(db_session, event=failed, payload=failed_payload)

    db_session.expire_all()
    order = db_session.get(Order, started.order_id)
    attempt = db_session.get(PaymentAttempt, started.payment_attempt_id)
    db_session.refresh(listing)
    assert order is not None and order.status == "pending_payment" and order.payment_status == "unpaid"
    assert order.inventory_released_at is None
    assert attempt is not None and attempt.status == "open"
    assert listing.available_quantity == 2
    assert db_session.scalar(
        select(func.count())
        .select_from(StripeWebhookEvent)
        .where(StripeWebhookEvent.stripe_event_id == "evt_terminal_rollback")
    ) == 0


def test_operator_reprocessing_uses_current_provider_state_without_public_replay_route(
    client: TestClient,
    db_session: Session,
) -> None:
    _buyer, listing, provider, started = start_local_payment(
        client,
        db_session,
        email="webhook-reprocess@example.com",
        quantity=1,
        available_quantity=3,
    )
    mismatched, mismatched_payload = checkout_event(
        event_id="evt_reprocess_amount",
        event_type="checkout.session.completed",
        started=started,
        provider=provider,
        payment_status="paid",
        session_status="complete",
    )
    mismatched["data"]["object"]["amount_total"] += 1
    mismatched_payload = json.dumps(mismatched, separators=(",", ":")).encode()
    stripe_webhooks.handle_verified_event(db_session, event=mismatched, payload=mismatched_payload)
    record = db_session.scalar(
        select(StripeWebhookEvent).where(StripeWebhookEvent.stripe_event_id == "evt_reprocess_amount")
    )
    assert record is not None and record.error_summary == "amount_mismatch"

    provider.set_session_state(
        started.provider_session_id,
        status="complete",
        payment_status="paid",
        payment_intent_id="pi_reprocessed",
    )
    outcome = stripe_webhooks.reprocess_stripe_event(
        db_session,
        stripe_event_id="evt_reprocess_amount",
        provider=provider,
    )
    replay = stripe_webhooks.reprocess_stripe_event(
        db_session,
        stripe_event_id="evt_reprocess_amount",
        provider=provider,
    )

    db_session.refresh(record)
    db_session.refresh(listing)
    order = db_session.get(Order, started.order_id)
    attempt = db_session.get(PaymentAttempt, started.payment_attempt_id)
    assert outcome.outcome == "paid"
    assert replay.outcome == "already_processed"
    assert record.processing_status == "processed" and record.error_summary is None
    assert order is not None and order.status == "confirmed" and order.payment_status == "paid"
    assert attempt is not None and attempt.status == "paid"
    assert listing.available_quantity == 2
    assert client.post("/api/v1/payments/stripe/reprocess").status_code == 404
