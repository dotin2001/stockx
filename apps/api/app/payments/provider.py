from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CheckoutSessionLineItem:
    name: str
    quantity: int
    unit_amount_cents: int


@dataclass(frozen=True, slots=True)
class CheckoutSessionRequest:
    order_id: str
    payment_attempt_id: str
    correlation_id: str
    customer_email: str
    currency: str
    line_items: tuple[CheckoutSessionLineItem, ...]
    success_url: str
    cancel_url: str
    expires_at: datetime
    provider_idempotency_key: str


@dataclass(frozen=True, slots=True)
class ProviderCheckoutSession:
    id: str
    payment_intent_id: str | None
    url: str | None
    status: str
    payment_status: str
    amount_total_cents: int
    currency: str
    livemode: bool
    expires_at: datetime
    metadata: dict[str, str]


class CheckoutSessionProvider(Protocol):
    def create_session(self, request: CheckoutSessionRequest) -> ProviderCheckoutSession: ...

    def retrieve_session(self, session_id: str) -> ProviderCheckoutSession: ...

    def expire_session(self, session_id: str) -> ProviderCheckoutSession: ...


class PaymentProviderError(RuntimeError):
    def __init__(self, message: str, *, definitive: bool) -> None:
        super().__init__(message)
        self.definitive = definitive
