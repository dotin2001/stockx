from __future__ import annotations

from datetime import UTC, datetime

import stripe

from app.payments import (
    CheckoutSessionLineItem,
    CheckoutSessionRequest,
    FakeCheckoutSessionProvider,
    StripeCheckoutSessionProvider,
)


def session_request() -> CheckoutSessionRequest:
    return CheckoutSessionRequest(
        order_id="order-123",
        payment_attempt_id="attempt-123",
        correlation_id="correlation-123",
        customer_email="buyer@example.com",
        currency="USD",
        line_items=(
            CheckoutSessionLineItem(name="First snapshot", quantity=2, unit_amount_cents=1250),
            CheckoutSessionLineItem(name="Second snapshot", quantity=1, unit_amount_cents=500),
        ),
        success_url="https://shop.example.com/orders/order-123?payment=return&session_id={CHECKOUT_SESSION_ID}",
        cancel_url="https://shop.example.com/orders/order-123?payment=cancelled",
        expires_at=datetime(2026, 10, 9, 12, 30, tzinfo=UTC),
        provider_idempotency_key="checkout-attempt-123",
    )


class SessionsStub:
    def __init__(self) -> None:
        self.create_calls: list[tuple[dict, dict]] = []
        self.retrieve_calls: list[str] = []
        self.expire_calls: list[str] = []
        self.session = {
            "id": "cs_test_123",
            "payment_intent": "pi_123",
            "url": "https://checkout.stripe.com/c/pay/cs_test_123",
            "status": "open",
            "payment_status": "unpaid",
            "amount_total": 3000,
            "currency": "usd",
            "livemode": False,
            "expires_at": 1791549000,
            "metadata": stripe.StripeObject.construct_from(
                {
                    "order_id": "order-123",
                    "payment_attempt_id": "attempt-123",
                    "correlation_id": "correlation-123",
                },
                "sk_test_example",
            ),
        }

    def create(self, params: dict, options: dict) -> dict:
        self.create_calls.append((params, options))
        return self.session

    def retrieve(self, session_id: str) -> dict:
        self.retrieve_calls.append(session_id)
        return self.session

    def expire(self, session_id: str) -> dict:
        self.expire_calls.append(session_id)
        return {**self.session, "status": "expired", "url": None}


class ClientStub:
    def __init__(self) -> None:
        self.sessions = SessionsStub()
        self.v1 = type("V1", (), {"checkout": type("Checkout", (), {"sessions": self.sessions})()})()


def test_stripe_adapter_uses_authoritative_session_contract() -> None:
    client = ClientStub()
    provider = StripeCheckoutSessionProvider("sk_test_example", client=client)

    created = provider.create_session(session_request())

    params, options = client.sessions.create_calls[0]
    assert params["mode"] == "payment"
    assert params["line_items"] == [
        {
            "price_data": {
                "currency": "usd",
                "unit_amount": 1250,
                "product_data": {"name": "First snapshot"},
            },
            "quantity": 2,
        },
        {
            "price_data": {
                "currency": "usd",
                "unit_amount": 500,
                "product_data": {"name": "Second snapshot"},
            },
            "quantity": 1,
        },
    ]
    assert params["customer_email"] == "buyer@example.com"
    assert params["client_reference_id"] == "correlation-123"
    assert params["metadata"] == {
        "order_id": "order-123",
        "payment_attempt_id": "attempt-123",
        "correlation_id": "correlation-123",
    }
    assert params["success_url"].endswith("session_id={CHECKOUT_SESSION_ID}")
    assert params["cancel_url"].endswith("payment=cancelled")
    assert params["expires_at"] == int(session_request().expires_at.timestamp())
    assert params["automatic_tax"] == {"enabled": False}
    assert "shipping_options" not in params
    assert "payment_method_types" not in params
    assert options == {"idempotency_key": "checkout-attempt-123"}
    assert created.amount_total_cents == 3000
    assert created.currency == "USD"
    assert created.payment_intent_id == "pi_123"
    assert created.metadata == params["metadata"]

    assert provider.retrieve_session(created.id).id == created.id
    assert provider.expire_session(created.id).status == "expired"
    assert client.sessions.retrieve_calls == [created.id]
    assert client.sessions.expire_calls == [created.id]


def test_fake_provider_is_deterministic_and_idempotent() -> None:
    provider = FakeCheckoutSessionProvider()
    request = session_request()

    first = provider.create_session(request)
    replay = provider.create_session(request)

    assert replay == first
    assert len(provider.requests) == 1
    assert first.amount_total_cents == 3000
    assert first.metadata["order_id"] == request.order_id
    assert provider.retrieve_session(first.id) == first
    expired = provider.expire_session(first.id)
    assert expired.status == "expired"
    assert expired.url is None
