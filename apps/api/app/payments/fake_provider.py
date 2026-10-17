from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from threading import Lock
from uuid import NAMESPACE_URL, uuid5

from app.payments.provider import CheckoutSessionRequest, PaymentProviderError, ProviderCheckoutSession


class FakeCheckoutSessionProvider:
    def __init__(self, *, livemode: bool = False) -> None:
        self.livemode = livemode
        self.sessions: dict[str, ProviderCheckoutSession] = {}
        self.session_ids_by_key: dict[str, str] = {}
        self.requests: list[CheckoutSessionRequest] = []
        self.next_error: PaymentProviderError | None = None
        self.retrieve_error: PaymentProviderError | None = None
        self.expire_error: PaymentProviderError | None = None
        self._lock = Lock()

    def create_session(self, request: CheckoutSessionRequest) -> ProviderCheckoutSession:
        with self._lock:
            existing_id = self.session_ids_by_key.get(request.provider_idempotency_key)
            if existing_id:
                return self.sessions[existing_id]
            if self.next_error:
                error, self.next_error = self.next_error, None
                raise error

            self.requests.append(request)
            token = uuid5(NAMESPACE_URL, request.provider_idempotency_key).hex
            session_id = f"cs_{'live' if self.livemode else 'test'}_{token}"
            session = ProviderCheckoutSession(
                id=session_id,
                payment_intent_id=None,
                url=f"https://checkout.stripe.com/c/pay/{session_id}",
                status="open",
                payment_status="unpaid",
                amount_total_cents=sum(item.unit_amount_cents * item.quantity for item in request.line_items),
                currency=request.currency.upper(),
                livemode=self.livemode,
                expires_at=request.expires_at.astimezone(UTC),
                metadata={
                    "order_id": request.order_id,
                    "payment_attempt_id": request.payment_attempt_id,
                    "correlation_id": request.correlation_id,
                },
            )
            self.sessions[session_id] = session
            self.session_ids_by_key[request.provider_idempotency_key] = session_id
            return session

    def retrieve_session(self, session_id: str) -> ProviderCheckoutSession:
        if self.retrieve_error:
            error, self.retrieve_error = self.retrieve_error, None
            raise error
        try:
            return self.sessions[session_id]
        except KeyError as exc:
            raise PaymentProviderError("Fake Checkout Session was not found", definitive=True) from exc

    def expire_session(self, session_id: str) -> ProviderCheckoutSession:
        if self.expire_error:
            error, self.expire_error = self.expire_error, None
            raise error
        session = self.retrieve_session(session_id)
        if session.status == "open":
            session = replace(session, status="expired", url=None)
            self.sessions[session_id] = session
        return session

    def set_session_state(
        self,
        session_id: str,
        *,
        status: str | None = None,
        payment_status: str | None = None,
        payment_intent_id: str | None = None,
    ) -> ProviderCheckoutSession:
        session = self.retrieve_session(session_id)
        session = replace(
            session,
            status=status or session.status,
            payment_status=payment_status or session.payment_status,
            payment_intent_id=payment_intent_id if payment_intent_id is not None else session.payment_intent_id,
            url=None if status == "expired" else session.url,
        )
        self.sessions[session_id] = session
        return session
