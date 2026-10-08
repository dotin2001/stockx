from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.errors import APIError
from app.core.config import CheckoutMode, settings
from app.models import CartItem, Category, Listing, Order, OrderItem, Product, User
from app.schemas.order import OrderCreateRequest
from app.services import checkout, orders


POSTGRES_URL = os.getenv("TEST_POSTGRES_DATABASE_URL")
pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason="TEST_POSTGRES_DATABASE_URL is not configured")


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
    assert POSTGRES_URL is not None
    engine = create_engine(POSTGRES_URL, pool_pre_ping=True)
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
