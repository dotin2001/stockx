from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import stripe

from app.payments.provider import CheckoutSessionRequest, PaymentProviderError, ProviderCheckoutSession
from app.payments.stripe_api import STRIPE_API_VERSION


def _value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def _resource_id(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return _value(value, "id")


class StripeCheckoutSessionProvider:
    def __init__(self, secret_key: str, *, client: Any | None = None) -> None:
        self.client = client or stripe.StripeClient(secret_key, stripe_version=STRIPE_API_VERSION)

    def create_session(self, request: CheckoutSessionRequest) -> ProviderCheckoutSession:
        params = {
            "mode": "payment",
            "line_items": [
                {
                    "price_data": {
                        "currency": request.currency.lower(),
                        "unit_amount": item.unit_amount_cents,
                        "product_data": {"name": item.name},
                    },
                    "quantity": item.quantity,
                }
                for item in request.line_items
            ],
            "customer_email": request.customer_email,
            "client_reference_id": request.correlation_id,
            "metadata": {
                "order_id": request.order_id,
                "payment_attempt_id": request.payment_attempt_id,
                "correlation_id": request.correlation_id,
            },
            "success_url": request.success_url,
            "cancel_url": request.cancel_url,
            "expires_at": int(request.expires_at.timestamp()),
            "automatic_tax": {"enabled": False},
            "allow_promotion_codes": False,
        }
        try:
            session = self.client.v1.checkout.sessions.create(
                params,
                {"idempotency_key": request.provider_idempotency_key},
            )
        except stripe.StripeError as exc:
            definitive = not isinstance(exc, (stripe.APIConnectionError, stripe.APIError))
            raise PaymentProviderError("Stripe Checkout Session creation failed", definitive=definitive) from exc
        return self._to_session(session)

    def retrieve_session(self, session_id: str) -> ProviderCheckoutSession:
        try:
            session = self.client.v1.checkout.sessions.retrieve(session_id)
        except stripe.StripeError as exc:
            raise PaymentProviderError("Stripe Checkout Session retrieval failed", definitive=False) from exc
        return self._to_session(session)

    def expire_session(self, session_id: str) -> ProviderCheckoutSession:
        try:
            session = self.client.v1.checkout.sessions.expire(session_id)
        except stripe.StripeError as exc:
            definitive = isinstance(exc, stripe.InvalidRequestError)
            raise PaymentProviderError("Stripe Checkout Session expiration failed", definitive=definitive) from exc
        return self._to_session(session)

    @staticmethod
    def _to_session(session: Any) -> ProviderCheckoutSession:
        metadata_value = _value(session, "metadata", {}) or {}
        if hasattr(metadata_value, "to_dict"):
            metadata_value = metadata_value.to_dict()
        metadata = dict(metadata_value)
        expires_at = _value(session, "expires_at")
        if expires_at is None:
            raise PaymentProviderError("Stripe response omitted session expiration", definitive=False)
        return ProviderCheckoutSession(
            id=str(_value(session, "id")),
            payment_intent_id=_resource_id(_value(session, "payment_intent")),
            url=_value(session, "url"),
            status=str(_value(session, "status", "open")),
            payment_status=str(_value(session, "payment_status", "unpaid")),
            amount_total_cents=int(_value(session, "amount_total", 0)),
            currency=str(_value(session, "currency", "")).upper(),
            livemode=bool(_value(session, "livemode", False)),
            expires_at=datetime.fromtimestamp(int(expires_at), tz=UTC),
            metadata={str(key): str(value) for key, value in metadata.items()},
        )
