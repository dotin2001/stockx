from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models import Order, OrderItem, PaymentAttempt, User
from app.schemas.order import AdminOrderSummary


def register_headers(client: TestClient, db: Session, email: str, *, role: str = "customer") -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"name": email.split("@", 1)[0], "email": email, "password": "password123"},
    )
    assert response.status_code == 201
    user = db.get(User, UUID(response.json()["user"]["id"]))
    assert user is not None
    if role in {"admin", "supreme"}:
        user.is_admin = True
    if role == "supreme":
        user.is_supreme_admin = True
    db.commit()
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def add_order(
    db: Session,
    *,
    user: User,
    number: str,
    email: str,
    status: str = "pending_payment",
    payment_status: str = "unpaid",
    quantity: int = 2,
    created_at: datetime | None = None,
    attempt_statuses: tuple[str, ...] = (),
) -> Order:
    now = datetime.now(timezone.utc)
    order = Order(
        order_number=number,
        user=user,
        idempotency_key=f"key-{number}",
        request_hash="0" * 64,
        status=status,
        payment_status=payment_status,
        currency="USD",
        subtotal_cents=12500 * quantity,
        shipping_cents=500,
        tax_cents=0,
        total_cents=12500 * quantity + 500,
        customer_name="Snapshot Buyer",
        customer_email=email,
        recipient_name="Snapshot Recipient",
        contact_email=email,
        contact_phone="+15555550101",
        address_line1="123 Snapshot Street",
        address_line2="Unit 4",
        city="Portland",
        state="OR",
        postal_code="97201",
        country="US",
        reservation_expires_at=now + timedelta(minutes=30),
        confirmed_at=now if status == "confirmed" else None,
    )
    order.items.extend(
        [
            OrderItem(
                product_name="Snapshot Sneaker",
                product_slug="snapshot-sneaker",
                product_image_url="https://example.test/snapshot.png",
                variant_label="Size 10",
                variant_sku="SNAP-10",
                variant_size="10",
                variant_color="Black",
                quantity=quantity,
                unit_price_cents=12500,
                line_total_cents=12500 * quantity,
            ),
            OrderItem(
                product_name="Snapshot Laces",
                product_slug="snapshot-laces",
                quantity=1,
                unit_price_cents=500,
                line_total_cents=500,
            ),
        ]
    )
    for index, attempt_status in enumerate(attempt_statuses):
        order.payment_attempts.append(
            PaymentAttempt(
                provider="stripe",
                status=attempt_status,
                amount_cents=order.total_cents,
                currency="USD",
                provider_session_id=f"cs_test_admin_{number}_{index}",
                provider_payment_intent_id=f"pi_admin_{number}_{index}",
                provider_livemode=False,
                hosted_url=f"https://checkout.stripe.com/c/pay/admin-secret-{index}",
                provider_idempotency_key=f"provider-secret-{number}-{index}",
                correlation_id=f"correlation-{number}-{index}",
                expires_at=now + timedelta(minutes=30),
                completed_at=now if attempt_status == "paid" else None,
                failure_code="provider_declined" if attempt_status == "failed" else None,
            )
        )
    db.add(order)
    db.commit()
    if created_at is not None:
        order.created_at = created_at
        for index, attempt in enumerate(order.payment_attempts):
            attempt.created_at = created_at + timedelta(seconds=index)
        db.commit()
    db.refresh(order)
    return order


def test_admin_summary_schema_accepts_supported_states_and_rejects_unsafe_fields() -> None:
    now = datetime.now(timezone.utc)
    base = {
        "id": uuid4(),
        "order_number": "STX-SCHEMA",
        "customer_name": "Buyer",
        "customer_email": "buyer@example.test",
        "status": "pending_payment",
        "payment_status": "unpaid",
        "currency": "USD",
        "total_cents": 1200,
        "item_line_count": 1,
        "item_quantity": 1,
        "confirmed_at": None,
        "created_at": now,
    }
    for attempt_status in ("initializing", "open", "processing", "paid", "failed", "expired", "cancelled"):
        attempt = {
            "id": uuid4(),
            "provider": "stripe",
            "status": attempt_status,
            "amount_cents": 1200,
            "currency": "USD",
            "expires_at": now,
            "completed_at": now if attempt_status == "paid" else None,
            "failure_code": "provider_declined" if attempt_status == "failed" else None,
        }
        assert AdminOrderSummary(**base, latest_payment_attempt=attempt).latest_payment_attempt is not None

    assert AdminOrderSummary(**base, latest_payment_attempt=None).payment_status.value == "unpaid"
    with pytest.raises(ValidationError):
        AdminOrderSummary(**{**base, "status": "shipped"})
    with pytest.raises(ValidationError):
        AdminOrderSummary(**base, provider_session_id="cs_test_secret")
    with pytest.raises(ValidationError):
        AdminOrderSummary(
            **base,
            latest_payment_attempt={
                "id": uuid4(),
                "provider": "stripe",
                "status": "open",
                "amount_cents": 1200,
                "currency": "USD",
                "expires_at": now,
                "hosted_url": "https://checkout.stripe.com/c/pay/secret",
            },
        )


def test_admin_order_routes_authorize_both_admin_roles_and_keep_customer_scope(
    client: TestClient,
    db_session: Session,
) -> None:
    customer_headers = register_headers(client, db_session, "owner@example.test")
    other_headers = register_headers(client, db_session, "other@example.test")
    admin_headers = register_headers(client, db_session, "admin@example.test", role="admin")
    supreme_headers = register_headers(client, db_session, "supreme@example.test", role="supreme")
    owner = db_session.query(User).filter_by(email="owner@example.test").one()
    order = add_order(db_session, user=owner, number="STX-AUTH", email=owner.email)

    for headers in (admin_headers, supreme_headers):
        response = client.get("/api/v1/admin/orders", headers=headers)
        assert response.status_code == 200
        assert response.json()["items"][0]["id"] == str(order.id)
        assert client.get(f"/api/v1/admin/orders/{order.id}", headers=headers).status_code == 200

    assert client.get("/api/v1/admin/orders").status_code == 401
    assert client.get("/api/v1/admin/orders", headers=customer_headers).status_code == 403
    assert client.get(f"/api/v1/admin/orders/{uuid4()}", headers=admin_headers).status_code == 404
    assert client.get(f"/api/v1/orders/{order.id}", headers=customer_headers).status_code == 200
    assert client.get(f"/api/v1/orders/{order.id}", headers=other_headers).status_code == 404


def test_admin_order_list_search_filters_pagination_counts_and_latest_attempt(
    client: TestClient,
    db_session: Session,
) -> None:
    admin_headers = register_headers(client, db_session, "list-admin@example.test", role="admin")
    owner_headers = register_headers(client, db_session, "list-owner@example.test")
    owner = db_session.query(User).filter_by(email="list-owner@example.test").one()
    shared_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    older = add_order(
        db_session,
        user=owner,
        number="STX-LITERAL-%_",
        email="special_%@example.test",
        status="pending_payment",
        payment_status="failed",
        quantity=2,
        created_at=shared_time,
        attempt_statuses=("open", "failed"),
    )
    newer = add_order(
        db_session,
        user=owner,
        number="STX-PAID-002",
        email="CaseSensitive@Example.test",
        status="confirmed",
        payment_status="paid",
        quantity=3,
        created_at=shared_time,
        attempt_statuses=("processing", "paid"),
    )
    expected = sorted((older, newer), key=lambda order: order.id, reverse=True)

    page = client.get("/api/v1/admin/orders?limit=1&offset=0", headers=admin_headers)
    assert page.status_code == 200
    assert page.json()["total"] == 2
    assert page.json()["limit"] == 1
    assert page.json()["offset"] == 0
    assert page.json()["items"][0]["id"] == str(expected[0].id)
    second_page = client.get("/api/v1/admin/orders?limit=1&offset=1", headers=admin_headers).json()
    assert second_page["items"][0]["id"] == str(expected[1].id)

    searched = client.get("/api/v1/admin/orders?search=casesensitive", headers=admin_headers).json()
    assert [item["id"] for item in searched["items"]] == [str(newer.id)]
    whitespace = client.get("/api/v1/admin/orders?search=%20%20%20", headers=admin_headers).json()
    assert whitespace["total"] == 2
    literal = client.get("/api/v1/admin/orders?search=%25_", headers=admin_headers).json()
    assert [item["id"] for item in literal["items"]] == [str(older.id)]
    combined = client.get(
        "/api/v1/admin/orders?status=confirmed&payment_status=paid&search=example.test",
        headers=admin_headers,
    ).json()
    assert [item["id"] for item in combined["items"]] == [str(newer.id)]
    assert combined["items"][0]["item_line_count"] == 2
    assert combined["items"][0]["item_quantity"] == 4
    assert combined["items"][0]["latest_payment_attempt"]["status"] == "paid"

    assert client.get("/api/v1/admin/orders?status=shipped", headers=admin_headers).status_code == 422
    assert client.get("/api/v1/admin/orders?payment_status=unknown", headers=admin_headers).status_code == 422
    assert client.get("/api/v1/admin/orders?limit=101", headers=admin_headers).status_code == 422
    assert client.get("/api/v1/admin/orders?offset=-1", headers=admin_headers).status_code == 422
    assert client.get("/api/v1/orders", headers=owner_headers).json()["total"] == 2


def test_admin_order_detail_uses_safe_immutable_snapshots(client: TestClient, db_session: Session) -> None:
    admin_headers = register_headers(client, db_session, "detail-admin@example.test", role="admin")
    register_headers(client, db_session, "detail-owner@example.test")
    owner = db_session.query(User).filter_by(email="detail-owner@example.test").one()
    order = add_order(
        db_session,
        user=owner,
        number="STX-DETAIL",
        email="original@example.test",
        status="confirmed",
        payment_status="paid",
        attempt_statuses=("open", "paid"),
    )
    owner.name = "Changed Live Name"
    owner.email = "changed-live@example.test"
    db_session.commit()

    response = client.get(f"/api/v1/admin/orders/{order.id}", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["customer_name"] == "Snapshot Buyer"
    assert body["customer_email"] == "original@example.test"
    assert body["shipping"]["address_line1"] == "123 Snapshot Street"
    assert body["items"][0]["product_name"] == "Snapshot Sneaker"
    assert body["total_cents"] == 25500
    assert body["payment_attempts"][-1]["status"] == "paid"
    serialized = response.text
    for forbidden in (
        "checkout.stripe.com",
        "provider-secret",
        "cs_test_admin",
        "pi_admin",
        "correlation-",
        '"request_hash"',
        '"idempotency_key"',
    ):
        assert forbidden not in serialized
