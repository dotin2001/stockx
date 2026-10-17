from __future__ import annotations

import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.errors import APIError
from app.core.config import CheckoutMode, settings
from app.models import CartItem, Listing, Order, PaymentAttempt, User
from app.payments import (
    CheckoutSessionLineItem,
    CheckoutSessionProvider,
    CheckoutSessionRequest,
    PaymentProviderError,
    ProviderCheckoutSession,
)
from app.schemas.order import PaymentCancellationRead, PaymentSessionCreateRequest, PaymentSessionRead
from app.services import orders
from app.services.customer_lock import lock_customer_row


@dataclass(slots=True)
class StripeReservation:
    order: Order
    attempt: PaymentAttempt
    replay: bool


@dataclass(frozen=True, slots=True)
class ReconciliationOutcome:
    attempt_id: str
    outcome: str
    detail: str | None = None


def checkout_session_request(reservation: StripeReservation) -> CheckoutSessionRequest:
    base_url = settings.frontend_base_url
    if not base_url:
        raise APIError(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "stripe_configuration_error",
            "Stripe checkout is not completely configured.",
        )
    order = reservation.order
    attempt = reservation.attempt
    return CheckoutSessionRequest(
        order_id=str(order.id),
        payment_attempt_id=str(attempt.id),
        correlation_id=attempt.correlation_id,
        customer_email=order.customer_email,
        currency=order.currency,
        line_items=tuple(
            CheckoutSessionLineItem(
                name=item.product_name if not item.variant_label else f"{item.product_name} — {item.variant_label}",
                quantity=item.quantity,
                unit_amount_cents=item.unit_price_cents,
            )
            for item in order.items
        ),
        success_url=(
            f"{base_url}/orders/{order.id}?payment=return&session_id={{CHECKOUT_SESSION_ID}}"
        ),
        cancel_url=f"{base_url}/orders/{order.id}?payment=cancelled",
        expires_at=attempt.expires_at,
        provider_idempotency_key=attempt.provider_idempotency_key,
    )


def create_provider_session(
    reservation: StripeReservation,
    *,
    provider: CheckoutSessionProvider,
) -> ProviderCheckoutSession:
    return provider.create_session(checkout_session_request(reservation))


def attach_provider_session(
    db: Session,
    *,
    attempt_id,
    provider_session: ProviderCheckoutSession,
) -> PaymentSessionRead:
    attempt = db.scalar(select(PaymentAttempt).where(PaymentAttempt.id == attempt_id).with_for_update())
    if attempt is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "payment_attempt_not_found", "Payment attempt was not found.")
    order = db.scalar(select(Order).where(Order.id == attempt.order_id).with_for_update())
    if order is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "order_not_found", "Order was not found.")

    expected_metadata = {
        "order_id": str(order.id),
        "payment_attempt_id": str(attempt.id),
        "correlation_id": attempt.correlation_id,
    }
    expiration_matches = int(provider_session.expires_at.timestamp()) == int(attempt.expires_at.timestamp())
    if (
        provider_session.status != "open"
        or not provider_session.url
        or provider_session.amount_total_cents != attempt.amount_cents
        or provider_session.currency != attempt.currency
        or provider_session.livemode != attempt.provider_livemode
        or not expiration_matches
        or provider_session.metadata != expected_metadata
    ):
        raise APIError(
            status.HTTP_502_BAD_GATEWAY,
            "provider_session_mismatch",
            "The payment provider returned a session that does not match the reserved order.",
        )

    attempt.provider_session_id = provider_session.id
    attempt.provider_payment_intent_id = provider_session.payment_intent_id
    attempt.hosted_url = provider_session.url
    attempt.status = "open"
    attempt.expires_at = provider_session.expires_at
    db.flush()
    return PaymentSessionRead(
        order_id=order.id,
        payment_attempt_id=attempt.id,
        provider_session_id=attempt.provider_session_id,
        status=attempt.status,
        url=attempt.hosted_url,
        expires_at=attempt.expires_at,
    )


def reserve_stripe_checkout(
    db: Session,
    *,
    user: User,
    payload: PaymentSessionCreateRequest,
    idempotency_key: str,
    now: datetime | None = None,
) -> StripeReservation:
    if settings.checkout_mode != CheckoutMode.STRIPE:
        raise APIError(status.HTTP_409_CONFLICT, "stripe_checkout_disabled", "Stripe checkout is not enabled.")

    request_hash = orders._request_hash(payload)
    lock_customer_row(db, user.id)
    existing = orders._existing_for_key(db, user_id=user.id, idempotency_key=idempotency_key)
    if existing is not None:
        if not hmac.compare_digest(existing.request_hash, request_hash):
            raise APIError(
                status.HTTP_409_CONFLICT,
                "idempotency_key_reused",
                "This idempotency key was already used for different checkout data.",
            )
        if not existing.payment_attempts:
            raise APIError(
                status.HTTP_409_CONFLICT,
                "payment_attempt_missing",
                "The existing checkout cannot be resumed automatically.",
            )
        return StripeReservation(order=existing, attempt=existing.payment_attempts[-1], replay=True)

    checkout_context = orders.lock_and_validate_checkout(db, user=user, payload=payload)
    started_at = now or datetime.now(timezone.utc)
    expires_at = started_at + timedelta(minutes=settings.stripe_reservation_minutes)
    order = orders.build_order_from_checkout(
        user=user,
        payload=payload,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        checkout_context=checkout_context,
        order_status="pending_payment",
        payment_status="unpaid",
        confirmed_at=None,
        reservation_expires_at=expires_at,
    )
    attempt_id = uuid4()
    attempt = PaymentAttempt(
        id=attempt_id,
        provider="stripe",
        status="initializing",
        amount_cents=order.total_cents,
        currency=order.currency,
        provider_livemode=settings.stripe_expected_livemode,
        provider_idempotency_key=f"stripe-checkout-{attempt_id}",
        correlation_id=uuid4().hex,
        expires_at=expires_at,
    )
    order.payment_attempts.append(attempt)
    orders.reserve_inventory_and_clear_cart(db, checkout_context=checkout_context)
    db.add(order)
    db.flush()
    return StripeReservation(order=order, attempt=attempt, replay=False)


def compensate_provider_failure(
    db: Session,
    *,
    attempt_id,
    failure_code: str = "provider_creation_failed",
    failure_message: str = "The payment provider could not create a checkout session.",
    now: datetime | None = None,
) -> StripeReservation:
    initial_attempt = db.get(PaymentAttempt, attempt_id)
    if initial_attempt is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "payment_attempt_not_found", "Payment attempt was not found.")
    initial_order = db.get(Order, initial_attempt.order_id)
    if initial_order is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "order_not_found", "Order was not found.")

    lock_customer_row(db, initial_order.user_id)
    order = db.scalar(
        select(Order)
        .where(Order.id == initial_order.id)
        .with_for_update()
        .options(selectinload(Order.items), selectinload(Order.payment_attempts))
        .execution_options(populate_existing=True)
    )
    attempt = db.scalar(
        select(PaymentAttempt)
        .where(PaymentAttempt.id == attempt_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if order is None or attempt is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "payment_attempt_not_found", "Payment attempt was not found.")
    if attempt.status == "paid" or order.payment_status == "paid":
        return StripeReservation(order=order, attempt=attempt, replay=True)
    if order.inventory_released_at is not None:
        return StripeReservation(order=order, attempt=attempt, replay=True)

    quantities_by_listing = {
        item.listing_id: item.quantity
        for item in order.items
        if item.listing_id is not None
    }
    listing_ids = sorted(quantities_by_listing, key=str)
    locked_listings = list(
        db.scalars(
            select(Listing)
            .where(Listing.id.in_(listing_ids))
            .order_by(Listing.id)
            .with_for_update()
        ).all()
    )
    if {listing.id for listing in locked_listings} != set(listing_ids):
        raise APIError(
            status.HTTP_409_CONFLICT,
            "reservation_source_missing",
            "Reserved inventory could not be restored safely.",
        )
    carts_by_listing = {
        item.listing_id: item
        for item in db.scalars(
            select(CartItem)
            .where(CartItem.user_id == order.user_id, CartItem.listing_id.in_(listing_ids))
            .order_by(CartItem.listing_id)
            .with_for_update()
        ).all()
    }
    for listing in locked_listings:
        quantity = quantities_by_listing[listing.id]
        listing.available_quantity += quantity
        cart_item = carts_by_listing.get(listing.id)
        if cart_item is None:
            db.add(CartItem(user_id=order.user_id, listing_id=listing.id, quantity=quantity))
        else:
            cart_item.quantity += quantity

    released_at = now or datetime.now(timezone.utc)
    order.status = "cancelled"
    order.payment_status = "failed"
    order.inventory_released_at = released_at
    attempt.status = "failed"
    attempt.failure_code = failure_code
    attempt.failure_message = failure_message[:255]
    attempt.hosted_url = None
    db.flush()
    return StripeReservation(order=order, attempt=attempt, replay=False)


def _open_session_response(reservation: StripeReservation) -> PaymentSessionRead | None:
    attempt = reservation.attempt
    if attempt.status != "open" or not attempt.provider_session_id or not attempt.hosted_url:
        return None
    return PaymentSessionRead(
        order_id=reservation.order.id,
        payment_attempt_id=attempt.id,
        provider_session_id=attempt.provider_session_id,
        status=attempt.status,
        url=attempt.hosted_url,
        expires_at=attempt.expires_at,
    )


def start_checkout_session(
    db: Session,
    *,
    user: User,
    payload: PaymentSessionCreateRequest,
    idempotency_key: str,
    provider: CheckoutSessionProvider,
    now: datetime | None = None,
) -> PaymentSessionRead:
    try:
        reservation = reserve_stripe_checkout(
            db,
            user=user,
            payload=payload,
            idempotency_key=idempotency_key,
            now=now,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    existing_response = _open_session_response(reservation)
    if existing_response is not None:
        return existing_response
    if reservation.attempt.status != "initializing":
        raise APIError(
            status.HTTP_409_CONFLICT,
            "payment_session_not_resumable",
            "This checkout attempt is no longer resumable.",
        )

    try:
        provider_session = create_provider_session(reservation, provider=provider)
    except PaymentProviderError as exc:
        if exc.definitive:
            try:
                compensate_provider_failure(db, attempt_id=reservation.attempt.id)
                db.commit()
            except Exception:
                db.rollback()
                raise
            raise APIError(
                status.HTTP_502_BAD_GATEWAY,
                "payment_provider_rejected",
                "Payment could not be started. Your cart and inventory reservation were restored.",
            ) from exc
        db.rollback()
        raise APIError(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "payment_provider_unavailable",
            "Payment provider status is uncertain. Retry with the same idempotency key.",
        ) from exc

    try:
        response = attach_provider_session(
            db,
            attempt_id=reservation.attempt.id,
            provider_session=provider_session,
        )
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise


def get_resumable_payment_session(
    db: Session,
    *,
    user: User,
    order_id,
    now: datetime | None = None,
) -> PaymentSessionRead:
    order = db.scalar(
        select(Order).where(
            Order.id == order_id,
            Order.user_id == user.id,
            Order.status == "pending_payment",
            Order.payment_status == "unpaid",
            Order.inventory_released_at.is_(None),
        )
    )
    if order is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "payment_session_not_found", "Payment session was not found.")
    attempt = db.scalar(
        select(PaymentAttempt)
        .where(
            PaymentAttempt.order_id == order.id,
            PaymentAttempt.status == "open",
            PaymentAttempt.provider_session_id.is_not(None),
            PaymentAttempt.hosted_url.is_not(None),
        )
        .order_by(PaymentAttempt.created_at.desc(), PaymentAttempt.id.desc())
    )
    current_time = now or datetime.now(timezone.utc)
    expires_at = attempt.expires_at if attempt is not None else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if attempt is None or expires_at.timestamp() <= current_time.timestamp():
        raise APIError(status.HTTP_404_NOT_FOUND, "payment_session_not_found", "Payment session was not found.")
    return PaymentSessionRead(
        order_id=attempt.order_id,
        payment_attempt_id=attempt.id,
        provider_session_id=attempt.provider_session_id,
        status=attempt.status,
        url=attempt.hosted_url,
        expires_at=attempt.expires_at,
    )


def _cancellation_read(order: Order, attempt: PaymentAttempt) -> PaymentCancellationRead:
    inventory_released_at = order.inventory_released_at
    if inventory_released_at is not None and inventory_released_at.tzinfo is None:
        inventory_released_at = inventory_released_at.replace(tzinfo=timezone.utc)
    return PaymentCancellationRead(
        order_id=order.id,
        order_status=order.status,
        payment_status=order.payment_status,
        attempt_status=attempt.status,
        inventory_released_at=inventory_released_at,
    )


def mark_payment_paid(
    db: Session,
    *,
    attempt_id,
    provider_session: ProviderCheckoutSession,
    now: datetime | None = None,
) -> PaymentCancellationRead:
    initial_attempt = db.get(PaymentAttempt, attempt_id)
    if initial_attempt is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "payment_attempt_not_found", "Payment attempt was not found.")
    initial_order = db.get(Order, initial_attempt.order_id)
    if initial_order is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "order_not_found", "Order was not found.")
    lock_customer_row(db, initial_order.user_id)
    order = db.scalar(
        select(Order)
        .where(Order.id == initial_order.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    attempt = db.scalar(
        select(PaymentAttempt)
        .where(PaymentAttempt.id == attempt_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if order is None or attempt is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "payment_attempt_not_found", "Payment attempt was not found.")
    if order.inventory_released_at is not None or order.status == "cancelled":
        return _cancellation_read(order, attempt)
    if (
        provider_session.id != attempt.provider_session_id
        or provider_session.payment_status != "paid"
        or provider_session.amount_total_cents != attempt.amount_cents
        or provider_session.currency != attempt.currency
        or provider_session.livemode != attempt.provider_livemode
    ):
        raise APIError(status.HTTP_409_CONFLICT, "provider_session_mismatch", "Provider payment state did not match the order.")
    completed_at = now or datetime.now(timezone.utc)
    attempt.status = "paid"
    attempt.provider_payment_intent_id = provider_session.payment_intent_id
    attempt.completed_at = completed_at
    attempt.hosted_url = None
    order.status = "confirmed"
    order.payment_status = "paid"
    order.confirmed_at = order.confirmed_at or completed_at
    db.flush()
    return _cancellation_read(order, attempt)


def release_terminal_reservation(
    db: Session,
    *,
    attempt_id,
    attempt_status: str,
    failure_code: str,
    now: datetime | None = None,
) -> PaymentCancellationRead:
    initial_attempt = db.get(PaymentAttempt, attempt_id)
    if initial_attempt is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "payment_attempt_not_found", "Payment attempt was not found.")
    initial_order = db.get(Order, initial_attempt.order_id)
    if initial_order is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "order_not_found", "Order was not found.")
    lock_customer_row(db, initial_order.user_id)
    order = db.scalar(
        select(Order)
        .where(Order.id == initial_order.id)
        .with_for_update()
        .options(selectinload(Order.items))
        .execution_options(populate_existing=True)
    )
    attempt = db.scalar(
        select(PaymentAttempt)
        .where(PaymentAttempt.id == attempt_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if order is None or attempt is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "payment_attempt_not_found", "Payment attempt was not found.")
    if attempt.status == "paid" or order.payment_status == "paid" or order.inventory_released_at is not None:
        return _cancellation_read(order, attempt)

    quantities_by_listing = {
        item.listing_id: item.quantity
        for item in order.items
        if item.listing_id is not None
    }
    listing_ids = sorted(quantities_by_listing, key=str)
    locked_listings = list(
        db.scalars(
            select(Listing)
            .where(Listing.id.in_(listing_ids))
            .order_by(Listing.id)
            .with_for_update()
        ).all()
    )
    for listing in locked_listings:
        listing.available_quantity += quantities_by_listing[listing.id]

    released_at = now or datetime.now(timezone.utc)
    attempt.status = attempt_status
    attempt.failure_code = failure_code
    attempt.hosted_url = None
    order.status = "cancelled"
    order.payment_status = "failed"
    order.inventory_released_at = released_at
    db.flush()
    return _cancellation_read(order, attempt)


def cancel_pending_payment(
    db: Session,
    *,
    user: User,
    order_id,
    provider: CheckoutSessionProvider,
) -> PaymentCancellationRead:
    order = db.scalar(
        select(Order)
        .where(Order.id == order_id, Order.user_id == user.id)
        .options(selectinload(Order.payment_attempts))
    )
    if order is None or not order.payment_attempts:
        raise APIError(status.HTTP_404_NOT_FOUND, "order_not_found", "Order was not found.")
    attempt = order.payment_attempts[-1]
    if order.payment_status == "paid" or order.inventory_released_at is not None or attempt.status in {
        "paid",
        "failed",
        "expired",
        "cancelled",
    }:
        return _cancellation_read(order, attempt)
    if not attempt.provider_session_id:
        result = release_terminal_reservation(
            db,
            attempt_id=attempt.id,
            attempt_status="cancelled",
            failure_code="customer_cancelled",
        )
        db.commit()
        return result

    session_id = attempt.provider_session_id
    attempt_id = attempt.id
    db.rollback()
    try:
        provider_session = provider.retrieve_session(session_id)
        if provider_session.payment_status == "paid":
            result = mark_payment_paid(db, attempt_id=attempt_id, provider_session=provider_session)
        else:
            expired_by_customer = False
            if provider_session.status == "open":
                provider_session = provider.expire_session(session_id)
                expired_by_customer = True
            if provider_session.payment_status == "paid":
                result = mark_payment_paid(db, attempt_id=attempt_id, provider_session=provider_session)
            else:
                terminal_status = "cancelled" if expired_by_customer else "expired"
                result = release_terminal_reservation(
                    db,
                    attempt_id=attempt_id,
                    attempt_status=terminal_status,
                    failure_code="session_expired" if terminal_status == "expired" else "customer_cancelled",
                )
        db.commit()
        return result
    except PaymentProviderError as exc:
        db.rollback()
        raise APIError(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "payment_provider_unavailable",
            "The payment provider could not confirm cancellation. Try again.",
        ) from exc
    except Exception:
        db.rollback()
        raise


def mark_payment_processing(
    db: Session,
    *,
    attempt_id,
    provider_session: ProviderCheckoutSession,
) -> None:
    initial_attempt = db.get(PaymentAttempt, attempt_id)
    if initial_attempt is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "payment_attempt_not_found", "Payment attempt was not found.")
    initial_order = db.get(Order, initial_attempt.order_id)
    if initial_order is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "order_not_found", "Order was not found.")
    lock_customer_row(db, initial_order.user_id)
    order = db.scalar(
        select(Order)
        .where(Order.id == initial_order.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    attempt = db.scalar(
        select(PaymentAttempt)
        .where(PaymentAttempt.id == attempt_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if order is None or attempt is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "payment_attempt_not_found", "Payment attempt was not found.")
    if attempt.status in {"paid", "failed", "expired", "cancelled"} or order.status != "pending_payment":
        return
    if (
        provider_session.id != attempt.provider_session_id
        or provider_session.amount_total_cents != attempt.amount_cents
        or provider_session.currency != attempt.currency
        or provider_session.livemode != attempt.provider_livemode
    ):
        raise APIError(status.HTTP_409_CONFLICT, "provider_session_mismatch", "Provider payment state did not match the order.")
    attempt.status = "processing"
    attempt.provider_payment_intent_id = provider_session.payment_intent_id
    attempt.hosted_url = None
    db.flush()


def reconcile_payment_attempt(
    db: Session,
    *,
    attempt_id,
    provider: CheckoutSessionProvider,
    now: datetime | None = None,
) -> ReconciliationOutcome:
    current_time = now or datetime.now(timezone.utc)
    attempt = db.scalar(
        select(PaymentAttempt)
        .where(PaymentAttempt.id == attempt_id)
        .options(selectinload(PaymentAttempt.order).selectinload(Order.items))
    )
    if attempt is None:
        return ReconciliationOutcome(str(attempt_id), "missing")
    order = attempt.order
    reservation = StripeReservation(order=order, attempt=attempt, replay=True)

    try:
        if attempt.status == "initializing":
            try:
                provider_session = create_provider_session(reservation, provider=provider)
            except PaymentProviderError as exc:
                if not exc.definitive:
                    db.rollback()
                    return ReconciliationOutcome(str(attempt.id), "provider_unavailable")
                compensate_provider_failure(db, attempt_id=attempt.id)
                db.commit()
                return ReconciliationOutcome(str(attempt.id), "compensated")
            attach_provider_session(db, attempt_id=attempt.id, provider_session=provider_session)
            db.commit()
            return ReconciliationOutcome(str(attempt.id), "session_recovered")

        if attempt.status in {"paid", "failed", "expired", "cancelled"}:
            return ReconciliationOutcome(str(attempt.id), "already_terminal", attempt.status)
        if not attempt.provider_session_id:
            return ReconciliationOutcome(str(attempt.id), "missing_provider_session")

        try:
            provider_session = provider.retrieve_session(attempt.provider_session_id)
        except PaymentProviderError:
            db.rollback()
            return ReconciliationOutcome(str(attempt.id), "provider_unavailable")

        if provider_session.payment_status == "paid":
            mark_payment_paid(db, attempt_id=attempt.id, provider_session=provider_session, now=current_time)
            db.commit()
            return ReconciliationOutcome(str(attempt.id), "paid")
        if provider_session.status == "complete":
            mark_payment_processing(db, attempt_id=attempt.id, provider_session=provider_session)
            db.commit()
            return ReconciliationOutcome(str(attempt.id), "processing")

        expires_at = order.reservation_expires_at or attempt.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if provider_session.status == "expired" or expires_at <= current_time:
            if provider_session.status == "open":
                try:
                    provider_session = provider.expire_session(provider_session.id)
                except PaymentProviderError:
                    db.rollback()
                    return ReconciliationOutcome(str(attempt.id), "provider_unavailable")
                if provider_session.payment_status == "paid":
                    mark_payment_paid(db, attempt_id=attempt.id, provider_session=provider_session, now=current_time)
                    db.commit()
                    return ReconciliationOutcome(str(attempt.id), "paid")
            release_terminal_reservation(
                db,
                attempt_id=attempt.id,
                attempt_status="expired",
                failure_code="session_expired",
                now=current_time,
            )
            db.commit()
            return ReconciliationOutcome(str(attempt.id), "expired")
        db.rollback()
        return ReconciliationOutcome(str(attempt.id), "still_open")
    except Exception:
        db.rollback()
        raise


def reconcile_stale_attempts(
    db: Session,
    *,
    provider: CheckoutSessionProvider,
    now: datetime | None = None,
    stale_minutes: int = 5,
    limit: int = 100,
) -> list[ReconciliationOutcome]:
    current_time = now or datetime.now(timezone.utc)
    stale_before = current_time - timedelta(minutes=stale_minutes)
    attempt_ids = list(
        db.scalars(
            select(PaymentAttempt.id)
            .join(Order)
            .where(
                or_(
                    and_(PaymentAttempt.status == "initializing", PaymentAttempt.updated_at <= stale_before),
                    and_(
                        PaymentAttempt.status.in_(("open", "processing")),
                        Order.status == "pending_payment",
                        Order.reservation_expires_at <= current_time,
                    ),
                )
            )
            .order_by(PaymentAttempt.updated_at, PaymentAttempt.id)
            .limit(limit)
        ).all()
    )
    db.rollback()
    return [
        reconcile_payment_attempt(db, attempt_id=attempt_id, provider=provider, now=current_time)
        for attempt_id in attempt_ids
    ]
