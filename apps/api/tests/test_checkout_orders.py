from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import CheckoutMode, Settings, settings
from app.core.security import hash_password
from app.models import CartItem, Category, Listing, Order, OrderItem, Product, ProductVariant, User
from app.schemas.order import OrderCreateRequest, ShippingAddress
from app.services import checkout, orders
from app.services.order_identifiers import generate_order_number, normalized_request_hash


SHIPPING = {
    "recipient_name": "Buyer Person",
    "contact_email": "buyer@example.com",
    "contact_phone": "+1 555 555 0101",
    "address_line1": "123 Market Street",
    "address_line2": "Suite 4",
    "city": "San Francisco",
    "state": "CA",
    "postal_code": "94105",
    "country": "US",
}


@pytest.fixture(autouse=True)
def restore_checkout_mode():
    previous = settings.checkout_mode
    try:
        yield
    finally:
        settings.checkout_mode = previous


def register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Checkout Buyer", "email": email, "password": "password123"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_cart_listing(
    db: Session,
    *,
    buyer_email: str,
    quantity: int = 2,
    available_quantity: int = 5,
    currency: str = "USD",
) -> tuple[User, Listing, CartItem]:
    buyer = db.scalar(select(User).where(User.email == buyer_email))
    assert buyer is not None
    product = db.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))
    assert product is not None
    seller = User(
        name="Store",
        email=f"store-{buyer_email}",
        password_hash=hash_password("password123"),
        is_admin=True,
    )
    listing = Listing(
        user=seller,
        product=product,
        product_variant=None,
        price_cents=25000,
        available_quantity=available_quantity,
        currency=currency,
        status="active",
    )
    cart_item = CartItem(user=buyer, listing=listing, quantity=quantity)
    db.add_all([seller, listing, cart_item])
    db.commit()
    db.refresh(listing)
    return buyer, listing, cart_item


def order_payload(token: str, **shipping_overrides: str) -> dict:
    return {"checkout_token": token, "shipping": {**SHIPPING, **shipping_overrides}}


def test_checkout_mode_defaults_disabled_and_rejects_unknown(monkeypatch) -> None:
    monkeypatch.delenv("CHECKOUT_MODE", raising=False)
    assert Settings(_env_file=None).checkout_mode == CheckoutMode.DISABLED
    assert Settings(checkout_mode="manual", _env_file=None).checkout_mode == CheckoutMode.MANUAL
    with pytest.raises(ValidationError):
        Settings(checkout_mode="automatic", _env_file=None)


def test_order_tables_constraints_and_source_foreign_keys() -> None:
    orders_table = Order.__table__
    items_table = OrderItem.__table__
    assert {"order_number", "user_id", "idempotency_key", "request_hash", "subtotal_cents", "total_cents"}.issubset(orders_table.c.keys())
    assert {"product_name", "product_slug", "variant_label", "unit_price_cents", "line_total_cents"}.issubset(items_table.c.keys())
    assert any(tuple(column.name for column in constraint.columns) == ("user_id", "idempotency_key") for constraint in orders_table.constraints if constraint.__class__.__name__ == "UniqueConstraint")
    foreign_keys = {fk.parent.name: fk.ondelete for fk in items_table.foreign_keys}
    assert foreign_keys["order_id"] == "CASCADE"
    assert foreign_keys["listing_id"] == "SET NULL"
    assert foreign_keys["product_id"] == "SET NULL"
    assert foreign_keys["product_variant_id"] == "SET NULL"


def test_order_number_and_normalized_hash_helpers() -> None:
    values = {generate_order_number() for _ in range(100)}
    assert len(values) == 100
    assert all(value.startswith("STX-") and len(value) == 20 for value in values)
    assert normalized_request_hash({"b": " two  spaces ", "a": "value"}) == normalized_request_hash({"a": "value", "b": "two spaces"})
    assert normalized_request_hash({"a": "one"}) != normalized_request_hash({"a": "two"})


def test_shipping_schema_normalizes_and_rejects_invalid_input() -> None:
    shipping = ShippingAddress(**{**SHIPPING, "recipient_name": "  Buyer   Person ", "country": "us"})
    assert shipping.recipient_name == "Buyer Person"
    assert shipping.country == "US"
    with pytest.raises(ValidationError):
        ShippingAddress(**{**SHIPPING, "postal_code": ""})
    with pytest.raises(ValidationError):
        ShippingAddress(**{**SHIPPING, "contact_email": "not-an-email"})


def test_checkout_summary_is_authoritative_deterministic_and_mode_aware(client: TestClient, db_session: Session) -> None:
    headers = register(client, "summary@example.com")
    buyer, listing, _item = create_cart_listing(db_session, buyer_email="summary@example.com")

    settings.checkout_mode = CheckoutMode.DISABLED
    first = client.get("/api/v1/checkout/summary", headers=headers)
    second = client.get("/api/v1/checkout/summary", headers=headers)
    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["subtotal_cents"] == 50000
    assert first.json()["shipping_cents"] == 0
    assert first.json()["tax_cents"] == 0
    assert first.json()["total_cents"] == 50000
    assert first.json()["order_placement_enabled"] is False

    settings.checkout_mode = CheckoutMode.MANUAL
    enabled = client.get("/api/v1/checkout/summary", headers=headers)
    assert enabled.status_code == 200
    assert enabled.json()["order_placement_enabled"] is True

    listing.price_cents += 1
    db_session.commit()
    changed = client.get("/api/v1/checkout/summary", headers=headers)
    assert changed.json()["checkout_token"] != first.json()["checkout_token"]

    empty_headers = register(client, "empty-checkout@example.com")
    empty = client.get("/api/v1/checkout/summary", headers=empty_headers)
    assert empty.status_code == 409
    assert empty.json()["error"]["code"] == "cart_empty"
    assert client.get("/api/v1/checkout/summary").status_code == 401


def test_checkout_summary_rejects_unavailable_archived_and_mixed_currency(client: TestClient, db_session: Session) -> None:
    headers = register(client, "conflicts@example.com")
    buyer, listing, item = create_cart_listing(db_session, buyer_email="conflicts@example.com", available_quantity=1)
    limited = client.get("/api/v1/checkout/summary", headers=headers)
    assert limited.status_code == 409
    assert limited.json()["error"]["code"] == "quantity_exceeds_availability"

    item.quantity = 1
    listing.product.archived_at = func.now()
    db_session.commit()
    archived = client.get("/api/v1/checkout/summary", headers=headers)
    assert archived.status_code == 409
    assert archived.json()["error"]["code"] == "product_archived"

    listing.product.archived_at = None
    second_product = Product(
        category=db_session.scalar(select(Category).where(Category.slug == "streetwear")),
        name="Other Currency Product",
        slug="other-currency-product",
        brand="Test",
        total_sold=0,
    )
    second_seller = User(name="Second Store", email="second-store@example.com", password_hash="unused", is_admin=True)
    second_listing = Listing(
        user=second_seller,
        product=second_product,
        price_cents=1000,
        available_quantity=2,
        currency="EUR",
        status="active",
    )
    db_session.add(CartItem(user=buyer, listing=second_listing, quantity=1))
    db_session.commit()
    mixed = client.get("/api/v1/checkout/summary", headers=headers)
    assert mixed.status_code == 409
    assert mixed.json()["error"]["code"] == "mixed_currency_cart"


def test_order_creation_is_atomic_idempotent_and_customer_scoped(client: TestClient, db_session: Session) -> None:
    owner_headers = register(client, "order-owner@example.com")
    other_headers = register(client, "order-other@example.com")
    buyer, listing, cart_item = create_cart_listing(db_session, buyer_email="order-owner@example.com", quantity=2)
    settings.checkout_mode = CheckoutMode.MANUAL
    summary = client.get("/api/v1/checkout/summary", headers=owner_headers).json()

    missing_key = client.post("/api/v1/orders", headers=owner_headers, json=order_payload(summary["checkout_token"]))
    assert missing_key.status_code == 422

    created = client.post(
        "/api/v1/orders",
        headers={**owner_headers, "Idempotency-Key": "attempt-1"},
        json=order_payload(summary["checkout_token"]),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "confirmed"
    assert body["payment_status"] == "unpaid"
    assert body["total_cents"] == 50000
    assert body["items"][0]["product_name"] == "Jordan 1 Retro High Test"
    db_session.refresh(listing)
    assert listing.available_quantity == 3
    assert db_session.get(CartItem, cart_item.id) is None
    assert db_session.scalar(select(func.count()).select_from(Order)) == 1

    replay = client.post(
        "/api/v1/orders",
        headers={**owner_headers, "Idempotency-Key": "attempt-1"},
        json=order_payload(summary["checkout_token"]),
    )
    assert replay.status_code == 201
    assert replay.json()["id"] == body["id"]
    db_session.refresh(listing)
    assert listing.available_quantity == 3
    assert db_session.scalar(select(func.count()).select_from(Order)) == 1

    conflict = client.post(
        "/api/v1/orders",
        headers={**owner_headers, "Idempotency-Key": "attempt-1"},
        json=order_payload(summary["checkout_token"], city="Oakland"),
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "idempotency_key_reused"

    history = client.get("/api/v1/orders", headers=owner_headers)
    assert history.status_code == 200
    assert history.json()["total"] == 1
    assert history.json()["items"][0]["id"] == body["id"]
    detail = client.get(f"/api/v1/orders/{body['id']}", headers=owner_headers)
    assert detail.status_code == 200
    assert client.get(f"/api/v1/orders/{body['id']}", headers=other_headers).status_code == 404
    assert client.get("/api/v1/orders").status_code == 401


def test_disabled_and_stale_checkout_leave_cart_inventory_and_orders_unchanged(client: TestClient, db_session: Session) -> None:
    headers = register(client, "unchanged@example.com")
    _buyer, listing, cart_item = create_cart_listing(db_session, buyer_email="unchanged@example.com", quantity=1)
    summary = client.get("/api/v1/checkout/summary", headers=headers).json()

    disabled = client.post(
        "/api/v1/orders",
        headers={**headers, "Idempotency-Key": "disabled-attempt"},
        json=order_payload(summary["checkout_token"]),
    )
    assert disabled.status_code == 409
    assert disabled.json()["error"]["code"] == "checkout_disabled"

    settings.checkout_mode = CheckoutMode.MANUAL
    listing.price_cents += 100
    db_session.commit()
    stale = client.post(
        "/api/v1/orders",
        headers={**headers, "Idempotency-Key": "stale-attempt"},
        json=order_payload(summary["checkout_token"]),
    )
    assert stale.status_code == 409
    assert stale.json()["error"]["code"] == "checkout_changed"
    db_session.refresh(listing)
    assert listing.available_quantity == 5
    assert db_session.get(CartItem, cart_item.id) is not None
    assert db_session.scalar(select(func.count()).select_from(Order)) == 0


def test_order_snapshots_survive_live_catalog_and_account_changes(client: TestClient, db_session: Session) -> None:
    headers = register(client, "snapshot@example.com")
    buyer, listing, _cart_item = create_cart_listing(db_session, buyer_email="snapshot@example.com", quantity=1)
    settings.checkout_mode = CheckoutMode.MANUAL
    summary = client.get("/api/v1/checkout/summary", headers=headers).json()
    created = client.post(
        "/api/v1/orders",
        headers={**headers, "Idempotency-Key": "snapshot-attempt"},
        json=order_payload(summary["checkout_token"]),
    ).json()

    buyer.name = "Changed Buyer"
    listing.product.name = "Changed Product"
    listing.price_cents = 1
    listing.available_quantity = 0
    db_session.commit()

    detail = client.get(f"/api/v1/orders/{created['id']}", headers=headers).json()
    assert detail["customer_name"] == "Checkout Buyer"
    assert detail["items"][0]["product_name"] == "Jordan 1 Retro High Test"
    assert detail["items"][0]["unit_price_cents"] == 25000
    assert detail["shipping"]["city"] == "San Francisco"


def test_forced_persistence_failure_rolls_back_order_inventory_and_cart(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    headers = register(client, "rollback@example.com")
    buyer, listing, cart_item = create_cart_listing(db_session, buyer_email="rollback@example.com", quantity=2)
    settings.checkout_mode = CheckoutMode.MANUAL
    summary = checkout.get_checkout_summary(db_session, user=buyer)
    payload = OrderCreateRequest(**order_payload(summary.checkout_token))
    original_flush = db_session.flush

    def fail_flush(*_args, **_kwargs):
        raise RuntimeError("forced persistence failure")

    monkeypatch.setattr(db_session, "flush", fail_flush)
    with pytest.raises(RuntimeError, match="forced persistence failure"):
        orders.create_order(
            db_session,
            user=buyer,
            payload=payload,
            idempotency_key="forced-failure",
        )
    db_session.rollback()
    monkeypatch.setattr(db_session, "flush", original_flush)

    db_session.refresh(listing)
    assert listing.available_quantity == 5
    assert db_session.get(CartItem, cart_item.id) is not None
    assert db_session.scalar(select(func.count()).select_from(Order)) == 0


def test_order_history_paginates_newest_first(client: TestClient, db_session: Session) -> None:
    headers = register(client, "pagination@example.com")
    buyer, listing, _cart_item = create_cart_listing(db_session, buyer_email="pagination@example.com", quantity=1)
    settings.checkout_mode = CheckoutMode.MANUAL

    first_summary = client.get("/api/v1/checkout/summary", headers=headers).json()
    first = client.post(
        "/api/v1/orders",
        headers={**headers, "Idempotency-Key": "page-first"},
        json=order_payload(first_summary["checkout_token"]),
    ).json()
    db_session.add(CartItem(user=buyer, listing=listing, quantity=1))
    db_session.commit()
    second_summary = client.get("/api/v1/checkout/summary", headers=headers).json()
    second = client.post(
        "/api/v1/orders",
        headers={**headers, "Idempotency-Key": "page-second"},
        json=order_payload(second_summary["checkout_token"]),
    ).json()

    first_order = db_session.get(Order, UUID(first["id"]))
    second_order = db_session.get(Order, UUID(second["id"]))
    assert first_order is not None and second_order is not None
    first_order.created_at = first_order.created_at.replace(year=2025)
    second_order.created_at = second_order.created_at.replace(year=2026)
    db_session.commit()

    first_page = client.get("/api/v1/orders?limit=1&offset=0", headers=headers).json()
    second_page = client.get("/api/v1/orders?limit=1&offset=1", headers=headers).json()
    assert first_page["total"] == 2
    assert first_page["items"][0]["id"] == second["id"]
    assert second_page["items"][0]["id"] == first["id"]
