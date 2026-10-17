from __future__ import annotations

from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.api.deps import get_checkout_provider
from app.core.config import CheckoutMode, settings
from app.models import CartItem, Listing, Order, PaymentAttempt
from app.payments import FakeCheckoutSessionProvider, PaymentProviderError
from app.reconcile_payments import main as reconcile_main
from app.schemas.order import PaymentSessionCreateRequest
from app.services import checkout, payment_checkout
from tests.test_checkout_orders import SHIPPING, create_cart_listing, order_payload, register


@pytest.fixture(autouse=True)
def stripe_mode():
    previous_mode = settings.checkout_mode
    previous_livemode = settings.stripe_expected_livemode
    previous_minutes = settings.stripe_reservation_minutes
    previous_base_url = settings.frontend_base_url
    settings.checkout_mode = CheckoutMode.STRIPE
    settings.stripe_expected_livemode = False
    settings.stripe_reservation_minutes = 30
    settings.frontend_base_url = "https://shop.example.com"
    try:
        yield
    finally:
        settings.checkout_mode = previous_mode
        settings.stripe_expected_livemode = previous_livemode
        settings.stripe_reservation_minutes = previous_minutes
        settings.frontend_base_url = previous_base_url


def payload_for(db: Session, buyer) -> PaymentSessionCreateRequest:
    summary = checkout.get_checkout_summary(db, user=buyer)
    return PaymentSessionCreateRequest(**order_payload(summary.checkout_token))


def test_local_stripe_reservation_creates_pending_order_attempt_and_reserves_inventory(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "stripe-reserve@example.com")
    buyer, listing, cart_item = create_cart_listing(
        db_session,
        buyer_email="stripe-reserve@example.com",
        quantity=2,
        available_quantity=5,
    )
    now = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)

    result = payment_checkout.reserve_stripe_checkout(
        db_session,
        user=buyer,
        payload=payload_for(db_session, buyer),
        idempotency_key="reserve-one",
        now=now,
    )

    assert result.replay is False
    assert result.order.status == "pending_payment"
    assert result.order.payment_status == "unpaid"
    assert result.order.confirmed_at is None
    assert result.order.reservation_expires_at == now + timedelta(minutes=30)
    assert result.attempt.status == "initializing"
    assert result.attempt.amount_cents == result.order.total_cents == 50000
    assert result.attempt.currency == "USD"
    assert result.attempt.expires_at == result.order.reservation_expires_at
    assert result.attempt.provider_idempotency_key == f"stripe-checkout-{result.attempt.id}"
    assert listing.available_quantity == 3
    assert db_session.get(CartItem, cart_item.id) is None
    assert db_session.scalar(select(func.count()).select_from(Order)) == 1
    assert db_session.scalar(select(func.count()).select_from(PaymentAttempt)) == 1


def test_stripe_reservation_rejects_stale_unavailable_and_mixed_currency(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "stripe-conflict@example.com")
    buyer, listing, item = create_cart_listing(db_session, buyer_email="stripe-conflict@example.com", quantity=1)
    payload = payload_for(db_session, buyer)
    listing.price_cents += 1
    db_session.flush()
    with pytest.raises(APIError) as stale:
        payment_checkout.reserve_stripe_checkout(
            db_session,
            user=buyer,
            payload=payload,
            idempotency_key="stale",
        )
    assert stale.value.code == "checkout_changed"
    db_session.rollback()

    item = db_session.get(CartItem, item.id)
    listing = db_session.get(Listing, listing.id)
    assert item is not None and listing is not None
    listing.available_quantity = 0
    db_session.flush()
    with pytest.raises(APIError) as unavailable:
        payment_checkout.reserve_stripe_checkout(
            db_session,
            user=buyer,
            payload=PaymentSessionCreateRequest(checkout_token="stale", shipping=SHIPPING),
            idempotency_key="unavailable",
        )
    assert unavailable.value.code == "listing_unavailable"
    db_session.rollback()

    item = db_session.get(CartItem, item.id)
    listing = db_session.get(Listing, listing.id)
    assert item is not None and listing is not None
    second_listing = Listing(
        user=listing.user,
        product=listing.product,
        price_cents=1000,
        available_quantity=2,
        currency="EUR",
        status="active",
    )
    db_session.add(CartItem(user=buyer, listing=second_listing, quantity=1))
    db_session.flush()
    with pytest.raises(APIError) as mixed:
        checkout.get_checkout_summary(db_session, user=buyer)
    assert mixed.value.code == "mixed_currency_cart"


def test_stripe_reservation_rolls_back_all_local_state_on_flush_failure(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    register(client, "stripe-rollback@example.com")
    buyer, listing, cart_item = create_cart_listing(db_session, buyer_email="stripe-rollback@example.com", quantity=2)
    payload = payload_for(db_session, buyer)

    def fail_flush(*_args, **_kwargs):
        raise RuntimeError("forced reservation failure")

    monkeypatch.setattr(db_session, "flush", fail_flush)
    with pytest.raises(RuntimeError, match="forced reservation failure"):
        payment_checkout.reserve_stripe_checkout(
            db_session,
            user=buyer,
            payload=payload,
            idempotency_key="rollback",
        )
    db_session.rollback()

    persisted_listing = db_session.get(Listing, listing.id)
    assert persisted_listing is not None and persisted_listing.available_quantity == 5
    assert db_session.get(CartItem, cart_item.id) is not None
    assert db_session.scalar(select(func.count()).select_from(Order)) == 0
    assert db_session.scalar(select(func.count()).select_from(PaymentAttempt)) == 0


def test_provider_session_is_server_derived_and_attached_after_reservation_commit(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "stripe-provider@example.com")
    buyer, _listing, _cart_item = create_cart_listing(
        db_session,
        buyer_email="stripe-provider@example.com",
        quantity=2,
    )
    reservation = payment_checkout.reserve_stripe_checkout(
        db_session,
        user=buyer,
        payload=payload_for(db_session, buyer),
        idempotency_key="provider-session",
        now=datetime(2026, 10, 9, 12, 0, tzinfo=UTC),
    )
    attempt_id = reservation.attempt.id
    db_session.commit()

    provider = FakeCheckoutSessionProvider()
    provider_session = payment_checkout.create_provider_session(reservation, provider=provider)
    response = payment_checkout.attach_provider_session(
        db_session,
        attempt_id=attempt_id,
        provider_session=provider_session,
    )
    db_session.commit()

    request = provider.requests[0]
    assert request.customer_email == "stripe-provider@example.com"
    assert request.currency == "USD"
    assert request.line_items[0].name == "Jordan 1 Retro High Test"
    assert request.line_items[0].quantity == 2
    assert request.line_items[0].unit_amount_cents == 25000
    assert sum(item.quantity * item.unit_amount_cents for item in request.line_items) == 50000
    assert request.success_url == (
        f"https://shop.example.com/orders/{reservation.order.id}"
        "?payment=return&session_id={CHECKOUT_SESSION_ID}"
    )
    assert request.cancel_url == f"https://shop.example.com/orders/{reservation.order.id}?payment=cancelled"
    assert request.expires_at == reservation.order.reservation_expires_at
    assert request.provider_idempotency_key == reservation.attempt.provider_idempotency_key
    assert provider_session.metadata == {
        "order_id": str(reservation.order.id),
        "payment_attempt_id": str(reservation.attempt.id),
        "correlation_id": reservation.attempt.correlation_id,
    }
    assert response.order_id == reservation.order.id
    assert str(response.url).startswith("https://checkout.stripe.com/")
    persisted = db_session.get(PaymentAttempt, attempt_id)
    assert persisted is not None
    assert persisted.status == "open"
    assert persisted.provider_session_id == provider_session.id
    assert persisted.hosted_url == provider_session.url


def test_definitive_provider_failure_compensates_inventory_and_cart_once(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "stripe-compensate@example.com")
    buyer, listing, _cart_item = create_cart_listing(
        db_session,
        buyer_email="stripe-compensate@example.com",
        quantity=2,
        available_quantity=5,
    )
    reservation = payment_checkout.reserve_stripe_checkout(
        db_session,
        user=buyer,
        payload=payload_for(db_session, buyer),
        idempotency_key="compensate",
    )
    attempt_id = reservation.attempt.id
    db_session.commit()
    assert listing.available_quantity == 3
    assert db_session.scalar(select(CartItem).where(CartItem.user_id == buyer.id)) is None

    compensated = payment_checkout.compensate_provider_failure(db_session, attempt_id=attempt_id)
    db_session.commit()
    db_session.refresh(listing)
    cart_item = db_session.scalar(select(CartItem).where(CartItem.user_id == buyer.id))
    assert cart_item is not None and cart_item.quantity == 2
    assert listing.available_quantity == 5
    assert compensated.order.status == "cancelled"
    assert compensated.order.payment_status == "failed"
    assert compensated.order.inventory_released_at is not None
    assert compensated.attempt.status == "failed"

    replay = payment_checkout.compensate_provider_failure(db_session, attempt_id=attempt_id)
    db_session.commit()
    db_session.refresh(listing)
    db_session.refresh(cart_item)
    assert replay.replay is True
    assert listing.available_quantity == 5
    assert cart_item.quantity == 2


def test_compensation_merges_with_a_concurrently_changed_cart(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "stripe-cart-merge@example.com")
    buyer, listing, _cart_item = create_cart_listing(
        db_session,
        buyer_email="stripe-cart-merge@example.com",
        quantity=2,
        available_quantity=6,
    )
    reservation = payment_checkout.reserve_stripe_checkout(
        db_session,
        user=buyer,
        payload=payload_for(db_session, buyer),
        idempotency_key="cart-merge",
    )
    attempt_id = reservation.attempt.id
    db_session.commit()
    db_session.add(CartItem(user_id=buyer.id, listing_id=listing.id, quantity=1))
    db_session.commit()

    payment_checkout.compensate_provider_failure(db_session, attempt_id=attempt_id)
    db_session.commit()

    cart_item = db_session.scalar(select(CartItem).where(CartItem.user_id == buyer.id, CartItem.listing_id == listing.id))
    db_session.refresh(listing)
    assert cart_item is not None and cart_item.quantity == 3
    assert listing.available_quantity == 6


def test_compensation_rolls_back_without_partial_restore(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    register(client, "stripe-compensate-rollback@example.com")
    buyer, listing, _cart_item = create_cart_listing(
        db_session,
        buyer_email="stripe-compensate-rollback@example.com",
        quantity=2,
        available_quantity=5,
    )
    reservation = payment_checkout.reserve_stripe_checkout(
        db_session,
        user=buyer,
        payload=payload_for(db_session, buyer),
        idempotency_key="compensation-rollback",
    )
    attempt_id = reservation.attempt.id
    db_session.commit()

    def fail_flush(*_args, **_kwargs):
        raise RuntimeError("forced compensation failure")

    monkeypatch.setattr(db_session, "flush", fail_flush)
    with pytest.raises(RuntimeError, match="forced compensation failure"):
        payment_checkout.compensate_provider_failure(db_session, attempt_id=attempt_id)
    db_session.rollback()

    order = db_session.get(Order, reservation.order.id)
    attempt = db_session.get(PaymentAttempt, attempt_id)
    db_session.refresh(listing)
    assert order is not None and order.status == "pending_payment"
    assert order.inventory_released_at is None
    assert attempt is not None and attempt.status == "initializing"
    assert listing.available_quantity == 3
    assert db_session.scalar(select(CartItem).where(CartItem.user_id == buyer.id)) is None


def test_checkout_initiation_replays_one_order_reservation_and_provider_session(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "stripe-idempotent@example.com")
    buyer, listing, _cart_item = create_cart_listing(
        db_session,
        buyer_email="stripe-idempotent@example.com",
        quantity=1,
        available_quantity=2,
    )
    payload = payload_for(db_session, buyer)
    provider = FakeCheckoutSessionProvider()

    first = payment_checkout.start_checkout_session(
        db_session,
        user=buyer,
        payload=payload,
        idempotency_key="one-attempt",
        provider=provider,
    )
    replay = payment_checkout.start_checkout_session(
        db_session,
        user=buyer,
        payload=payload,
        idempotency_key="one-attempt",
        provider=provider,
    )

    assert replay == first
    assert len(provider.requests) == 1
    assert db_session.scalar(select(func.count()).select_from(Order)) == 1
    assert db_session.scalar(select(func.count()).select_from(PaymentAttempt)) == 1
    db_session.refresh(listing)
    assert listing.available_quantity == 1

    changed = PaymentSessionCreateRequest(
        checkout_token=payload.checkout_token,
        shipping={**SHIPPING, "city": "Different"},
    )
    with pytest.raises(APIError) as conflict:
        payment_checkout.start_checkout_session(
            db_session,
            user=buyer,
            payload=changed,
            idempotency_key="one-attempt",
            provider=provider,
        )
    assert conflict.value.code == "idempotency_key_reused"


class AcceptThenLoseResponseProvider:
    def __init__(self) -> None:
        self.delegate = FakeCheckoutSessionProvider()
        self.lost_response = False

    def create_session(self, request):
        session = self.delegate.create_session(request)
        if not self.lost_response:
            self.lost_response = True
            raise PaymentProviderError("response lost", definitive=False)
        return session

    def retrieve_session(self, session_id):
        return self.delegate.retrieve_session(session_id)

    def expire_session(self, session_id):
        return self.delegate.expire_session(session_id)


def test_ambiguous_provider_failure_recovers_with_the_same_provider_idempotency_key(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "stripe-ambiguous@example.com")
    buyer, listing, _cart_item = create_cart_listing(
        db_session,
        buyer_email="stripe-ambiguous@example.com",
        quantity=1,
        available_quantity=2,
    )
    payload = payload_for(db_session, buyer)
    provider = AcceptThenLoseResponseProvider()

    with pytest.raises(APIError) as uncertain:
        payment_checkout.start_checkout_session(
            db_session,
            user=buyer,
            payload=payload,
            idempotency_key="ambiguous",
            provider=provider,
        )
    assert uncertain.value.code == "payment_provider_unavailable"
    attempt = db_session.scalar(select(PaymentAttempt))
    assert attempt is not None and attempt.status == "initializing"
    db_session.refresh(listing)
    assert listing.available_quantity == 1

    recovered = payment_checkout.start_checkout_session(
        db_session,
        user=buyer,
        payload=payload,
        idempotency_key="ambiguous",
        provider=provider,
    )
    assert recovered.provider_session_id in provider.delegate.sessions
    assert len(provider.delegate.requests) == 1


def test_retry_recovers_crash_between_provider_creation_and_attachment(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "stripe-attach-recovery@example.com")
    buyer, _listing, _cart_item = create_cart_listing(
        db_session,
        buyer_email="stripe-attach-recovery@example.com",
        quantity=1,
    )
    payload = payload_for(db_session, buyer)
    provider = FakeCheckoutSessionProvider()
    reservation = payment_checkout.reserve_stripe_checkout(
        db_session,
        user=buyer,
        payload=payload,
        idempotency_key="attach-recovery",
    )
    db_session.commit()
    orphaned_response = payment_checkout.create_provider_session(reservation, provider=provider)

    recovered = payment_checkout.start_checkout_session(
        db_session,
        user=buyer,
        payload=payload,
        idempotency_key="attach-recovery",
        provider=provider,
    )
    assert recovered.provider_session_id == orphaned_response.id
    assert len(provider.requests) == 1


def test_checkout_session_api_requires_authentication_key_and_stripe_mode(
    client: TestClient,
    db_session: Session,
) -> None:
    provider = FakeCheckoutSessionProvider()
    client.app.dependency_overrides[get_checkout_provider] = lambda: provider
    unauthenticated = client.post(
        "/api/v1/checkout/sessions",
        headers={"Idempotency-Key": "unauthenticated"},
        json={"checkout_token": "token", "shipping": SHIPPING},
    )
    assert unauthenticated.status_code == 401

    headers = register(client, "stripe-api-gates@example.com")
    buyer, _listing, _cart_item = create_cart_listing(db_session, buyer_email="stripe-api-gates@example.com")
    payload = payload_for(db_session, buyer).model_dump(mode="json")
    assert client.post("/api/v1/checkout/sessions", headers=headers, json=payload).status_code == 422

    for mode in (CheckoutMode.DISABLED, CheckoutMode.MANUAL):
        settings.checkout_mode = mode
        response = client.post(
            "/api/v1/checkout/sessions",
            headers={**headers, "Idempotency-Key": f"mode-{mode.value}"},
            json=payload,
        )
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "stripe_checkout_disabled"


def test_checkout_session_api_success_replay_conflict_and_provider_failure(
    client: TestClient,
    db_session: Session,
) -> None:
    provider = FakeCheckoutSessionProvider()
    client.app.dependency_overrides[get_checkout_provider] = lambda: provider
    headers = register(client, "stripe-api@example.com")
    buyer, listing, _cart_item = create_cart_listing(
        db_session,
        buyer_email="stripe-api@example.com",
        quantity=1,
        available_quantity=3,
    )
    payload = payload_for(db_session, buyer).model_dump(mode="json")
    request_headers = {**headers, "Idempotency-Key": "api-attempt"}

    created = client.post("/api/v1/checkout/sessions", headers=request_headers, json=payload)
    assert created.status_code == 201
    assert created.json()["url"].startswith("https://checkout.stripe.com/")
    replay = client.post("/api/v1/checkout/sessions", headers=request_headers, json=payload)
    assert replay.status_code == 201
    assert replay.json() == created.json()
    conflict = client.post(
        "/api/v1/checkout/sessions",
        headers=request_headers,
        json={**payload, "shipping": {**SHIPPING, "city": "Different"}},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_key_reused"

    db_session.add(CartItem(user_id=buyer.id, listing_id=listing.id, quantity=1))
    db_session.commit()
    failure_payload = payload_for(db_session, buyer).model_dump(mode="json")
    provider.next_error = PaymentProviderError("declined", definitive=True)
    failed = client.post(
        "/api/v1/checkout/sessions",
        headers={**headers, "Idempotency-Key": "api-provider-failure"},
        json=failure_payload,
    )
    assert failed.status_code == 502
    assert failed.json()["error"]["code"] == "payment_provider_rejected"
    db_session.refresh(listing)
    assert listing.available_quantity == 2


def test_checkout_session_api_reports_incomplete_stripe_configuration(
    client: TestClient,
    db_session: Session,
) -> None:
    client.app.dependency_overrides.pop(get_checkout_provider, None)
    previous_secret = settings.stripe_secret_key
    settings.stripe_secret_key = None
    headers = register(client, "stripe-config-api@example.com")
    buyer, _listing, _cart_item = create_cart_listing(db_session, buyer_email="stripe-config-api@example.com")
    try:
        response = client.post(
            "/api/v1/checkout/sessions",
            headers={**headers, "Idempotency-Key": "config-error"},
            json=payload_for(db_session, buyer).model_dump(mode="json"),
        )
    finally:
        settings.stripe_secret_key = previous_secret
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "stripe_configuration_error"


def test_payment_session_lookup_is_owner_scoped_and_only_returns_resumable_attempts(
    client: TestClient,
    db_session: Session,
) -> None:
    provider = FakeCheckoutSessionProvider()
    client.app.dependency_overrides[get_checkout_provider] = lambda: provider
    owner_headers = register(client, "stripe-resume-owner@example.com")
    other_headers = register(client, "stripe-resume-other@example.com")
    buyer, _listing, _cart_item = create_cart_listing(
        db_session,
        buyer_email="stripe-resume-owner@example.com",
        quantity=1,
    )
    created = client.post(
        "/api/v1/checkout/sessions",
        headers={**owner_headers, "Idempotency-Key": "resume-session"},
        json=payload_for(db_session, buyer).model_dump(mode="json"),
    ).json()
    order_id = created["order_id"]
    db_session.expire_all()

    own = client.get(f"/api/v1/orders/{order_id}/payment-session", headers=owner_headers)
    assert own.status_code == 200, own.text
    assert own.json()["url"] == created["url"]
    assert client.get(f"/api/v1/orders/{order_id}/payment-session", headers=other_headers).status_code == 404
    assert client.get(f"/api/v1/orders/{order_id}/payment-session").status_code == 401
    assert client.get(f"/api/v1/orders/{UUID(int=0)}/payment-session", headers=owner_headers).status_code == 404

    attempt = db_session.get(PaymentAttempt, UUID(created["payment_attempt_id"]))
    assert attempt is not None
    attempt.status = "expired"
    attempt.hosted_url = None
    db_session.commit()
    assert client.get(f"/api/v1/orders/{order_id}/payment-session", headers=owner_headers).status_code == 404


def test_cancel_pending_payment_expires_provider_and_releases_inventory_once(
    client: TestClient,
    db_session: Session,
) -> None:
    provider = FakeCheckoutSessionProvider()
    client.app.dependency_overrides[get_checkout_provider] = lambda: provider
    headers = register(client, "stripe-cancel@example.com")
    buyer, listing, _cart_item = create_cart_listing(
        db_session,
        buyer_email="stripe-cancel@example.com",
        quantity=2,
        available_quantity=5,
    )
    created = client.post(
        "/api/v1/checkout/sessions",
        headers={**headers, "Idempotency-Key": "cancel-session"},
        json=payload_for(db_session, buyer).model_dump(mode="json"),
    ).json()
    order_id = created["order_id"]

    cancelled = client.post(f"/api/v1/orders/{order_id}/cancel-payment", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["order_status"] == "cancelled"
    assert cancelled.json()["payment_status"] == "failed"
    assert cancelled.json()["attempt_status"] == "cancelled"
    db_session.refresh(listing)
    assert listing.available_quantity == 5
    assert db_session.scalar(select(CartItem).where(CartItem.user_id == buyer.id)) is None

    replay = client.post(f"/api/v1/orders/{order_id}/cancel-payment", headers=headers)
    assert replay.status_code == 200
    assert replay.json() == cancelled.json()
    db_session.refresh(listing)
    assert listing.available_quantity == 5


def test_cancel_pending_payment_respects_expired_paid_provider_and_provider_errors(
    client: TestClient,
    db_session: Session,
) -> None:
    provider = FakeCheckoutSessionProvider()
    client.app.dependency_overrides[get_checkout_provider] = lambda: provider
    headers = register(client, "stripe-cancel-states@example.com")
    buyer, listing, _cart_item = create_cart_listing(
        db_session,
        buyer_email="stripe-cancel-states@example.com",
        quantity=1,
        available_quantity=4,
    )

    first = client.post(
        "/api/v1/checkout/sessions",
        headers={**headers, "Idempotency-Key": "expired-session"},
        json=payload_for(db_session, buyer).model_dump(mode="json"),
    ).json()
    provider.set_session_state(first["provider_session_id"], status="expired")
    expired = client.post(f"/api/v1/orders/{first['order_id']}/cancel-payment", headers=headers)
    assert expired.status_code == 200
    assert expired.json()["attempt_status"] == "expired"

    db_session.add(CartItem(user_id=buyer.id, listing_id=listing.id, quantity=1))
    db_session.commit()
    paid = client.post(
        "/api/v1/checkout/sessions",
        headers={**headers, "Idempotency-Key": "paid-session"},
        json=payload_for(db_session, buyer).model_dump(mode="json"),
    ).json()
    provider.set_session_state(
        paid["provider_session_id"],
        status="complete",
        payment_status="paid",
        payment_intent_id="pi_paid_cancel_race",
    )
    paid_result = client.post(f"/api/v1/orders/{paid['order_id']}/cancel-payment", headers=headers)
    assert paid_result.status_code == 200
    assert paid_result.json()["order_status"] == "confirmed"
    assert paid_result.json()["payment_status"] == "paid"
    assert paid_result.json()["attempt_status"] == "paid"

    db_session.add(CartItem(user_id=buyer.id, listing_id=listing.id, quantity=1))
    db_session.commit()
    errored = client.post(
        "/api/v1/checkout/sessions",
        headers={**headers, "Idempotency-Key": "provider-error-session"},
        json=payload_for(db_session, buyer).model_dump(mode="json"),
    ).json()
    provider.retrieve_error = PaymentProviderError("temporary", definitive=False)
    provider_error = client.post(f"/api/v1/orders/{errored['order_id']}/cancel-payment", headers=headers)
    assert provider_error.status_code == 503
    assert provider_error.json()["error"]["code"] == "payment_provider_unavailable"
    attempt = db_session.get(PaymentAttempt, UUID(errored["payment_attempt_id"]))
    assert attempt is not None and attempt.status == "open"


def test_cancel_pending_payment_is_owner_scoped_and_authenticated(
    client: TestClient,
    db_session: Session,
) -> None:
    provider = FakeCheckoutSessionProvider()
    client.app.dependency_overrides[get_checkout_provider] = lambda: provider
    owner_headers = register(client, "stripe-cancel-owner@example.com")
    other_headers = register(client, "stripe-cancel-other@example.com")
    buyer, _listing, _cart_item = create_cart_listing(db_session, buyer_email="stripe-cancel-owner@example.com")
    created = client.post(
        "/api/v1/checkout/sessions",
        headers={**owner_headers, "Idempotency-Key": "cancel-owner"},
        json=payload_for(db_session, buyer).model_dump(mode="json"),
    ).json()
    url = f"/api/v1/orders/{created['order_id']}/cancel-payment"
    assert client.post(url, headers=other_headers).status_code == 404
    assert client.post(url).status_code == 401


def test_reconciliation_recovers_initializing_and_compensates_definitive_failure(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "stripe-reconcile-init@example.com")
    buyer, listing, _cart_item = create_cart_listing(
        db_session,
        buyer_email="stripe-reconcile-init@example.com",
        quantity=1,
        available_quantity=3,
    )
    payload = payload_for(db_session, buyer)
    provider = FakeCheckoutSessionProvider()
    reservation = payment_checkout.reserve_stripe_checkout(
        db_session,
        user=buyer,
        payload=payload,
        idempotency_key="reconcile-initializing",
    )
    attempt_id = reservation.attempt.id
    db_session.commit()

    recovered = payment_checkout.reconcile_payment_attempt(
        db_session,
        attempt_id=attempt_id,
        provider=provider,
    )
    assert recovered.outcome == "session_recovered"
    assert len(provider.requests) == 1

    db_session.add(CartItem(user_id=buyer.id, listing_id=listing.id, quantity=1))
    db_session.commit()
    second = payment_checkout.reserve_stripe_checkout(
        db_session,
        user=buyer,
        payload=payload_for(db_session, buyer),
        idempotency_key="reconcile-definitive-failure",
    )
    second_id = second.attempt.id
    db_session.commit()
    provider.next_error = PaymentProviderError("rejected", definitive=True)
    compensated = payment_checkout.reconcile_payment_attempt(
        db_session,
        attempt_id=second_id,
        provider=provider,
    )
    assert compensated.outcome == "compensated"
    db_session.refresh(listing)
    assert listing.available_quantity == 2
    restored = db_session.scalar(select(CartItem).where(CartItem.user_id == buyer.id))
    assert restored is not None and restored.quantity == 1


def test_reconciliation_confirms_paid_preserves_processing_and_expires_unpaid(
    client: TestClient,
    db_session: Session,
) -> None:
    register(client, "stripe-reconcile-states@example.com")
    buyer, listing, _cart_item = create_cart_listing(
        db_session,
        buyer_email="stripe-reconcile-states@example.com",
        quantity=1,
        available_quantity=3,
    )
    provider = FakeCheckoutSessionProvider()
    started = payment_checkout.start_checkout_session(
        db_session,
        user=buyer,
        payload=payload_for(db_session, buyer),
        idempotency_key="reconcile-states",
        provider=provider,
    )
    provider.set_session_state(started.provider_session_id, status="complete", payment_status="unpaid")
    processing = payment_checkout.reconcile_payment_attempt(
        db_session,
        attempt_id=started.payment_attempt_id,
        provider=provider,
    )
    assert processing.outcome == "processing"
    attempt = db_session.get(PaymentAttempt, started.payment_attempt_id)
    assert attempt is not None and attempt.status == "processing"
    db_session.refresh(listing)
    assert listing.available_quantity == 2

    provider.set_session_state(
        started.provider_session_id,
        status="complete",
        payment_status="paid",
        payment_intent_id="pi_reconciled",
    )
    paid = payment_checkout.reconcile_payment_attempt(
        db_session,
        attempt_id=started.payment_attempt_id,
        provider=provider,
    )
    assert paid.outcome == "paid"
    order = db_session.get(Order, started.order_id)
    assert order is not None and order.status == "confirmed" and order.payment_status == "paid"

    db_session.add(CartItem(user_id=buyer.id, listing_id=listing.id, quantity=1))
    db_session.commit()
    expiring = payment_checkout.start_checkout_session(
        db_session,
        user=buyer,
        payload=payload_for(db_session, buyer),
        idempotency_key="reconcile-expired",
        provider=provider,
    )
    provider.set_session_state(expiring.provider_session_id, status="expired", payment_status="unpaid")
    expired = payment_checkout.reconcile_payment_attempt(
        db_session,
        attempt_id=expiring.payment_attempt_id,
        provider=provider,
    )
    assert expired.outcome == "expired"
    db_session.refresh(listing)
    assert listing.available_quantity == 2


def test_reconciliation_command_reports_safe_per_attempt_outcomes(
    client: TestClient,
    db_session: Session,
    capsys,
) -> None:
    register(client, "stripe-reconcile-cli@example.com")
    buyer, _listing, _cart_item = create_cart_listing(db_session, buyer_email="stripe-reconcile-cli@example.com")
    provider = FakeCheckoutSessionProvider()
    reservation = payment_checkout.reserve_stripe_checkout(
        db_session,
        user=buyer,
        payload=payload_for(db_session, buyer),
        idempotency_key="reconcile-cli",
        now=datetime.now(UTC) - timedelta(minutes=10),
    )
    attempt_id = reservation.attempt.id
    db_session.commit()

    exit_code = reconcile_main(
        ["--stale-minutes", "0", "--limit", "10"],
        session_factory=lambda: nullcontext(db_session),
        provider_factory=lambda: provider,
    )
    output = capsys.readouterr().out
    assert exit_code == 0
    assert str(attempt_id) in output
    assert "session_recovered" in output
    assert "sk_test" not in output
    assert "whsec" not in output
    assert "checkout.stripe.com" not in output
