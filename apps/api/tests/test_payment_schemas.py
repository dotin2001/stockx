from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.order import (
    PaymentAttemptStatus,
    PaymentAttemptSummary,
    PaymentCancellationRead,
    PaymentSessionCreateRequest,
    PaymentSessionRead,
)
from tests.test_checkout_orders import SHIPPING


NOW = datetime(2026, 10, 9, 12, 0, tzinfo=UTC)


@pytest.mark.parametrize("status", list(PaymentAttemptStatus))
def test_payment_attempt_summary_accepts_all_lifecycle_states(status: PaymentAttemptStatus) -> None:
    summary = PaymentAttemptSummary(
        id=uuid4(),
        provider="stripe",
        status=status,
        amount_cents=1250,
        currency="USD",
        expires_at=NOW,
        completed_at=NOW if status == PaymentAttemptStatus.PAID else None,
        failure_code="provider_declined" if status == PaymentAttemptStatus.FAILED else None,
    )
    assert summary.status == status


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount_cents": 0},
        {"amount_cents": -1},
        {"currency": "usd"},
        {"currency": "US"},
        {"provider": "other"},
        {"id": "not-a-uuid"},
        {"failure_code": "unsafe failure text"},
    ],
)
def test_payment_attempt_summary_rejects_invalid_money_currency_and_identifiers(overrides: dict) -> None:
    payload = {
        "id": uuid4(),
        "provider": "stripe",
        "status": "open",
        "amount_cents": 1250,
        "currency": "USD",
        "expires_at": NOW,
        **overrides,
    }
    with pytest.raises(ValidationError):
        PaymentAttemptSummary(**payload)


def test_payment_session_schema_accepts_only_stripe_hosted_urls_and_ids() -> None:
    payload = {
        "order_id": uuid4(),
        "payment_attempt_id": uuid4(),
        "provider_session_id": "cs_test_valid123",
        "status": "open",
        "url": "https://checkout.stripe.com/c/pay/cs_test_valid123",
        "expires_at": NOW,
    }
    assert PaymentSessionRead(**payload).status == PaymentAttemptStatus.OPEN

    for overrides in (
        {"provider_session_id": "pi_123"},
        {"url": "http://checkout.stripe.com/c/pay/cs_test_valid123"},
        {"url": "https://evil.example/cs_test_valid123"},
        {"payment_attempt_id": "not-a-uuid"},
    ):
        with pytest.raises(ValidationError):
            PaymentSessionRead(**{**payload, **overrides})


def test_payment_requests_reject_client_supplied_authoritative_values() -> None:
    valid = {"checkout_token": "token", "shipping": SHIPPING}
    assert PaymentSessionCreateRequest(**valid).checkout_token == "token"
    for field, value in (
        ("amount_cents", 1),
        ("currency", "USD"),
        ("provider_session_id", "cs_test_123"),
        ("total_cents", 1),
    ):
        with pytest.raises(ValidationError):
            PaymentSessionCreateRequest(**{**valid, field: value})


def test_cancellation_schema_accepts_terminal_payment_states() -> None:
    result = PaymentCancellationRead(
        order_id=uuid4(),
        order_status="cancelled",
        payment_status="failed",
        attempt_status="expired",
        inventory_released_at=NOW,
    )
    assert result.attempt_status == PaymentAttemptStatus.EXPIRED
