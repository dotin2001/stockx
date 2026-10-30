from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.errors import APIError
from app.core.config import CheckoutMode, settings
from app.models import CartItem, Category, Listing, Order, OrderItem, PaymentAttempt, Product, StripeWebhookEvent, User
from app.payments import FakeCheckoutSessionProvider
from app.schemas.order import OrderCreateRequest, PaymentSessionCreateRequest
from app.services import checkout, orders, payment_checkout
from app.services import stripe_webhooks
from tests.postgres_support import create_postgres_test_engine


def shipping_payload(token: str) -> OrderCreateRequest:
    return OrderCreateRequest(
        checkout_token=token,
        shipping={
            "recipient_name": "Concurrency Buyer",
            "contact_email": "concurrency@example.com",
            "contact_phone": "+1 555 555 0101",
            "address_line1": "1 Locking Lane",
            "city": "Postgres",
            "state": "DB",
            "postal_code": "00001",
            "country": "US",
        },
    )


@pytest.fixture()
def postgres_checkout_data():
    engine = create_postgres_test_engine()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    suffix = uuid4().hex
    with SessionLocal() as db:
        category = Category(name=f"Concurrency {suffix}", slug=f"concurrency-{suffix}")
        product = Product(category=category, name="Final Unit", slug=f"final-unit-{suffix}", total_sold=0)
        seller = User(name="Concurrency Store", email=f"store-{suffix}@example.test", password_hash="unused", is_admin=True)
        first = User(name="First Buyer", email=f"first-{suffix}@example.test", password_hash="unused")
        second = User(name="Second Buyer", email=f"second-{suffix}@example.test", password_hash="unused")
        listing = Listing(user=seller, product=product, price_cents=12345, available_quantity=1, currency="USD", status="active")
        db.add_all([CartItem(user=first, listing=listing, quantity=1), CartItem(user=second, listing=listing, quantity=1)])
        db.commit()
        ids = {
            "category": category.id,
            "product": product.id,
            "listing": listing.id,
            "users": [seller.id, first.id, second.id],
            "buyers": [first.id, second.id],
        }
        tokens = {
            user.id: checkout.get_checkout_summary(db, user=user).checkout_token
            for user in (first, second)
        }
    previous_mode = settings.checkout_mode
    settings.checkout_mode = CheckoutMode.MANUAL
    try:
        yield SessionLocal, ids, tokens
    finally:
        settings.checkout_mode = previous_mode
        with SessionLocal() as db:
            db.execute(delete(OrderItem).where(OrderItem.order_id.in_(select(Order.id).where(Order.user_id.in_(ids["buyers"])))))
            db.execute(delete(Order).where(Order.user_id.in_(ids["buyers"])))
            db.execute(delete(CartItem).where(CartItem.user_id.in_(ids["buyers"])))
            db.execute(delete(Listing).where(Listing.id == ids["listing"]))
            db.execute(delete(Product).where(Product.id == ids["product"]))
            db.execute(delete(Category).where(Category.id == ids["category"]))
            db.execute(delete(User).where(User.id.in_(ids["users"])))
            db.commit()
        engine.dispose()


def test_two_customers_competing_for_final_unit(postgres_checkout_data) -> None:
    SessionLocal, ids, tokens = postgres_checkout_data

    def attempt(user_id):
        with SessionLocal() as db:
            user = db.get(User, user_id)
            assert user is not None
            try:
                result = orders.create_order(
                    db,
                    user=user,
                    payload=shipping_payload(tokens[user_id]),
                    idempotency_key=f"final-unit-{user_id}",
                )
                db.commit()
                return ("success", user_id, result.id)
            except APIError as exc:
                db.rollback()
                return (exc.code, user_id, None)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, ids["buyers"]))

    assert sum(result[0] == "success" for result in results) == 1
    assert sum(result[0] in {"listing_unavailable", "quantity_exceeds_availability"} for result in results) == 1
    winner_id = next(result[1] for result in results if result[0] == "success")
    loser_id = next(result[1] for result in results if result[0] != "success")
    with SessionLocal() as db:
        listing = db.get(Listing, ids["listing"])
        assert listing is not None and listing.available_quantity == 0
        assert db.get(Product, ids["product"]).lowest_ask_cents is None
        assert db.scalar(select(CartItem).where(CartItem.user_id == winner_id)) is None
        assert db.scalar(select(CartItem).where(CartItem.user_id == loser_id)) is not None


def test_concurrent_same_customer_retry_creates_one_order(postgres_checkout_data) -> None:
    SessionLocal, ids, tokens = postgres_checkout_data
    user_id = ids["buyers"][0]
    payload = shipping_payload(tokens[user_id])

    def attempt(_index: int):
        with SessionLocal() as db:
            user = db.get(User, user_id)
            assert user is not None
            result = orders.create_order(
                db,
                user=user,
                payload=payload,
                idempotency_key="same-concurrent-attempt",
            )
            db.commit()
            return result.id

    with ThreadPoolExecutor(max_workers=2) as executor:
        order_ids = list(executor.map(attempt, range(2)))

    assert order_ids[0] == order_ids[1]
    with SessionLocal() as db:
        assert len(db.scalars(select(Order).where(Order.user_id == user_id)).all()) == 1
        listing = db.get(Listing, ids["listing"])
        assert listing is not None and listing.available_quantity == 0
        assert db.get(Product, ids["product"]).lowest_ask_cents is None


def test_two_customers_competing_for_final_stripe_reservation(postgres_checkout_data) -> None:
    SessionLocal, ids, tokens = postgres_checkout_data
    previous_mode = settings.checkout_mode
    settings.checkout_mode = CheckoutMode.STRIPE

    def attempt(user_id):
        with SessionLocal() as db:
            user = db.get(User, user_id)
            assert user is not None
            try:
                result = payment_checkout.reserve_stripe_checkout(
                    db,
                    user=user,
                    payload=PaymentSessionCreateRequest.model_validate(shipping_payload(tokens[user_id]).model_dump()),
                    idempotency_key=f"stripe-final-unit-{user_id}",
                )
                db.commit()
                return ("success", user_id, result.order.id)
            except APIError as exc:
                db.rollback()
                return (exc.code, user_id, None)

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(attempt, ids["buyers"]))
    finally:
        settings.checkout_mode = previous_mode

    assert sum(result[0] == "success" for result in results) == 1
    assert sum(result[0] in {"listing_unavailable", "quantity_exceeds_availability"} for result in results) == 1
    with SessionLocal() as db:
        listing = db.get(Listing, ids["listing"])
        assert listing is not None and listing.available_quantity == 0
        assert (
            db.scalar(
                select(func.count())
                .select_from(PaymentAttempt)
                .join(Order)
                .where(Order.user_id.in_(ids["buyers"]))
            )
            == 1
        )


def test_concurrent_same_customer_stripe_retry_creates_one_provider_session(postgres_checkout_data) -> None:
    SessionLocal, ids, tokens = postgres_checkout_data
    user_id = ids["buyers"][0]
    payload = PaymentSessionCreateRequest.model_validate(shipping_payload(tokens[user_id]).model_dump())
    provider = FakeCheckoutSessionProvider()
    previous_mode = settings.checkout_mode
    previous_base_url = settings.frontend_base_url
    settings.checkout_mode = CheckoutMode.STRIPE
    settings.frontend_base_url = "https://shop.example.com"

    def attempt(_index: int):
        with SessionLocal() as db:
            user = db.get(User, user_id)
            assert user is not None
            return payment_checkout.start_checkout_session(
                db,
                user=user,
                payload=payload,
                idempotency_key="same-stripe-concurrent-attempt",
                provider=provider,
            )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(attempt, range(2)))
    finally:
        settings.checkout_mode = previous_mode
        settings.frontend_base_url = previous_base_url

    assert results[0].order_id == results[1].order_id
    assert results[0].provider_session_id == results[1].provider_session_id
    assert len(provider.requests) == 1
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Order).where(Order.user_id == user_id)) == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(PaymentAttempt)
                .join(Order)
                .where(Order.user_id == user_id)
            )
            == 1
        )


def test_paid_provider_state_wins_concurrent_customer_cancellation(postgres_checkout_data) -> None:
    SessionLocal, ids, tokens = postgres_checkout_data
    user_id = ids["buyers"][0]
    payload = PaymentSessionCreateRequest.model_validate(shipping_payload(tokens[user_id]).model_dump())
    provider = FakeCheckoutSessionProvider()
    previous_mode = settings.checkout_mode
    previous_base_url = settings.frontend_base_url
    settings.checkout_mode = CheckoutMode.STRIPE
    settings.frontend_base_url = "https://shop.example.com"
    try:
        with SessionLocal() as db:
            user = db.get(User, user_id)
            assert user is not None
            started = payment_checkout.start_checkout_session(
                db,
                user=user,
                payload=payload,
                idempotency_key="paid-cancel-race",
                provider=provider,
            )
        paid_session = provider.set_session_state(
            started.provider_session_id,
            status="complete",
            payment_status="paid",
            payment_intent_id="pi_paid_cancel_concurrency",
        )

        def cancel():
            with SessionLocal() as db:
                user = db.get(User, user_id)
                assert user is not None
                return payment_checkout.cancel_pending_payment(
                    db,
                    user=user,
                    order_id=started.order_id,
                    provider=provider,
                )

        def confirm_paid():
            with SessionLocal() as db:
                result = payment_checkout.mark_payment_paid(
                    db,
                    attempt_id=started.payment_attempt_id,
                    provider_session=paid_session,
                )
                db.commit()
                return result

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda fn: fn(), (cancel, confirm_paid)))
    finally:
        settings.checkout_mode = previous_mode
        settings.frontend_base_url = previous_base_url

    assert all(result.payment_status == "paid" for result in results)
    with SessionLocal() as db:
        order = db.get(Order, started.order_id)
        listing = db.get(Listing, ids["listing"])
        assert order is not None and order.status == "confirmed" and order.payment_status == "paid"
        assert order.inventory_released_at is None
        assert listing is not None and listing.available_quantity == 0
        assert db.get(Product, ids["product"]).lowest_ask_cents is None


def test_concurrent_paid_and_expired_transitions_keep_inventory_consistent(postgres_checkout_data) -> None:
    SessionLocal, ids, tokens = postgres_checkout_data
    user_id = ids["buyers"][0]
    payload = PaymentSessionCreateRequest.model_validate(shipping_payload(tokens[user_id]).model_dump())
    provider = FakeCheckoutSessionProvider()
    previous_mode = settings.checkout_mode
    previous_base_url = settings.frontend_base_url
    settings.checkout_mode = CheckoutMode.STRIPE
    settings.frontend_base_url = "https://shop.example.com"
    try:
        with SessionLocal() as db:
            user = db.get(User, user_id)
            assert user is not None
            started = payment_checkout.start_checkout_session(
                db,
                user=user,
                payload=payload,
                idempotency_key="paid-expired-race",
                provider=provider,
            )
        paid_session = provider.set_session_state(
            started.provider_session_id,
            status="complete",
            payment_status="paid",
            payment_intent_id="pi_paid_expired_concurrency",
        )

        def confirm_paid():
            with SessionLocal() as db:
                result = payment_checkout.mark_payment_paid(
                    db,
                    attempt_id=started.payment_attempt_id,
                    provider_session=paid_session,
                )
                db.commit()
                return result.payment_status

        def expire_unpaid():
            with SessionLocal() as db:
                result = payment_checkout.release_terminal_reservation(
                    db,
                    attempt_id=started.payment_attempt_id,
                    attempt_status="expired",
                    failure_code="session_expired",
                )
                db.commit()
                return result.payment_status

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda fn: fn(), (confirm_paid, expire_unpaid)))
    finally:
        settings.checkout_mode = previous_mode
        settings.frontend_base_url = previous_base_url

    assert len(set(results)) == 1
    with SessionLocal() as db:
        order = db.get(Order, started.order_id)
        attempt = db.get(PaymentAttempt, started.payment_attempt_id)
        listing = db.get(Listing, ids["listing"])
        assert order is not None and attempt is not None and listing is not None
        if order.payment_status == "paid":
            assert order.status == "confirmed" and attempt.status == "paid"
            assert order.inventory_released_at is None and listing.available_quantity == 0
            assert db.get(Product, ids["product"]).lowest_ask_cents is None
        else:
            assert order.status == "cancelled" and order.payment_status == "failed"
            assert attempt.status == "expired"
            assert order.inventory_released_at is not None and listing.available_quantity == 1
            assert db.get(Product, ids["product"]).lowest_ask_cents == 12345


def test_concurrent_duplicate_webhook_insert_is_deduplicated(postgres_checkout_data) -> None:
    SessionLocal, _ids, _tokens = postgres_checkout_data
    event = {
        "id": f"evt_concurrent_{uuid4().hex}",
        "type": "checkout.session.completed",
        "livemode": False,
        "data": {"object": {"id": f"cs_test_{uuid4().hex}"}},
    }
    payload = str(event).encode()

    def deliver(_index: int):
        with SessionLocal() as db:
            return stripe_webhooks.handle_verified_event(db, event=event, payload=payload)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(deliver, range(2)))

    assert results == [{"received": True}, {"received": True}]
    with SessionLocal() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(StripeWebhookEvent)
                .where(StripeWebhookEvent.stripe_event_id == event["id"])
            )
            == 1
        )
