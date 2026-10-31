from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import (
    Category,
    Listing,
    Order,
    PaymentAttempt,
    Product,
    ProductVariant,
    RefreshToken,
    StripeWebhookEvent,
    User,
)
from app.services.refresh_token_retention import (
    delete_refresh_token_batch,
    preview_refresh_token_cleanup,
)
from tests.postgres_support import assert_explicit_test_database, create_postgres_test_engine


# Keep integration fixtures far outside normal application data so a developer's
# explicitly selected local test database cannot affect batch counts or have its
# recent refresh tokens selected by these tests.
NOW = datetime(2000, 2, 1, 12, 0, tzinfo=UTC)
CUTOFF = NOW - timedelta(days=30)


def token(
    user: User,
    *,
    expires_at: datetime,
    revoked_at: datetime | None = None,
) -> RefreshToken:
    return RefreshToken(
        user=user,
        token_hash=f"retention-{uuid4().hex}",
        expires_at=expires_at,
        revoked_at=revoked_at,
        created_at=NOW - timedelta(days=90),
    )


@pytest.fixture()
def postgres_retention_data():
    engine = create_postgres_test_engine()
    assert_explicit_test_database(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    suffix = uuid4().hex
    with SessionLocal() as db:
        user = User(
            name="Retention PostgreSQL User",
            email=f"retention-{suffix}@example.test",
            password_hash="unused",
        )
        db.add(user)
        db.flush()
        records = {
            "expiry_boundary": token(user, expires_at=CUTOFF),
            "revocation_boundary": token(
                user,
                expires_at=NOW + timedelta(days=10),
                revoked_at=CUTOFF,
            ),
            "oldest": token(user, expires_at=CUTOFF - timedelta(days=10)),
            "recent_expiry": token(user, expires_at=CUTOFF + timedelta(microseconds=1)),
            "recent_revocation": token(
                user,
                expires_at=NOW + timedelta(days=10),
                revoked_at=CUTOFF + timedelta(microseconds=1),
            ),
            "active": token(user, expires_at=NOW + timedelta(days=10)),
        }
        protected_replacement = token(user, expires_at=NOW + timedelta(days=20))
        eligible_predecessor = token(user, expires_at=CUTOFF - timedelta(days=5))
        eligible_predecessor.replaced_by_token = protected_replacement
        protected_incoming = token(user, expires_at=NOW + timedelta(days=30))
        eligible_target = token(user, expires_at=CUTOFF - timedelta(days=4))
        protected_incoming.replaced_by_token = eligible_target
        records.update(
            {
                "protected_replacement": protected_replacement,
                "eligible_predecessor": eligible_predecessor,
                "protected_incoming": protected_incoming,
                "eligible_target": eligible_target,
            }
        )
        db.add_all(records.values())
        db.commit()
        ids = {name: record.id for name, record in records.items()}
        user_id = user.id

    try:
        yield SessionLocal, ids
    finally:
        with SessionLocal() as db:
            db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
            db.execute(delete(User).where(User.id == user_id))
            db.commit()
        engine.dispose()


def test_postgres_boundaries_dry_run_batches_idempotency_and_replacement_links(
    postgres_retention_data,
) -> None:
    SessionLocal, ids = postgres_retention_data
    with SessionLocal() as db:
        before = set(db.scalars(select(RefreshToken.id)).all())
        with db.begin_nested():
            preview = preview_refresh_token_cleanup(db, cutoff=CUTOFF, batch_size=3)
        assert preview.selected_count == 3
        assert set(db.scalars(select(RefreshToken.id)).all()) == before

    deleted_total = 0
    counts: list[int] = []
    while True:
        with SessionLocal.begin() as db:
            result = delete_refresh_token_batch(db, cutoff=CUTOFF, batch_size=2)
            counts.append(result.deleted_count)
            deleted_total += result.deleted_count
        if result.deleted_count == 0:
            break

    assert counts == [2, 2, 1, 0]
    assert deleted_total == 5
    with SessionLocal() as db:
        remaining = set(db.scalars(select(RefreshToken.id)).all())
        assert ids["expiry_boundary"] not in remaining
        assert ids["revocation_boundary"] not in remaining
        assert ids["oldest"] not in remaining
        assert ids["eligible_predecessor"] not in remaining
        assert ids["eligible_target"] not in remaining
        assert ids["recent_expiry"] in remaining
        assert ids["recent_revocation"] in remaining
        assert ids["active"] in remaining
        assert ids["protected_replacement"] in remaining
        incoming = db.get(RefreshToken, ids["protected_incoming"])
        assert incoming is not None and incoming.replaced_by_token_id is None


def test_postgres_skip_locked_deletion_reports_only_rows_actually_deleted(
    postgres_retention_data,
) -> None:
    SessionLocal, ids = postgres_retention_data
    locked_session = SessionLocal()
    try:
        locked_session.begin()
        locked_session.scalar(
            select(RefreshToken.id)
            .where(RefreshToken.id == ids["oldest"])
            .with_for_update()
        )
        with SessionLocal.begin() as worker:
            result = delete_refresh_token_batch(worker, cutoff=CUTOFF, batch_size=2)
        assert result.selected_count == 2
        assert result.deleted_count == 2
        with SessionLocal() as verifier:
            assert verifier.get(RefreshToken, ids["oldest"]) is not None
    finally:
        locked_session.rollback()
        locked_session.close()


def test_postgres_cleanup_preserves_business_payment_webhook_and_catalog_rows() -> None:
    engine = create_postgres_test_engine()
    assert_explicit_test_database(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    suffix = uuid4().hex
    with SessionLocal.begin() as db:
        category = Category(name=f"Retention {suffix}", slug=f"retention-{suffix}")
        user = User(
            name="Protected Retention User",
            email=f"protected-retention-{suffix}@example.test",
            password_hash="unused",
            is_admin=True,
        )
        product = Product(category=category, name="Protected Product", slug=f"protected-{suffix}")
        variant = ProductVariant(product=product, size="10", color="Black", sku=f"RET-{suffix}")
        listing = Listing(
            user=user,
            product=product,
            product_variant=variant,
            price_cents=10000,
            available_quantity=1,
            currency="USD",
            status="active",
        )
        order = Order(
            order_number=f"RET-{suffix[:20]}",
            user=user,
            idempotency_key=f"retention-{suffix}",
            request_hash="a" * 64,
            status="pending_payment",
            payment_status="unpaid",
            currency="USD",
            subtotal_cents=10000,
            shipping_cents=0,
            tax_cents=0,
            total_cents=10000,
            customer_name="Protected User",
            customer_email=user.email,
            recipient_name="Protected User",
            contact_email=user.email,
            contact_phone="+15555550100",
            address_line1="1 Retention Way",
            city="Postgres",
            state="DB",
            postal_code="00001",
            country="US",
        )
        payment = PaymentAttempt(
            order=order,
            provider="stripe",
            status="failed",
            amount_cents=10000,
            currency="USD",
            provider_livemode=False,
            provider_idempotency_key=f"pi-key-{suffix}",
            correlation_id=f"corr-{suffix}",
            expires_at=CUTOFF - timedelta(days=100),
            completed_at=CUTOFF - timedelta(days=100),
        )
        webhook = StripeWebhookEvent(
            stripe_event_id=f"evt_{suffix}",
            event_type="checkout.session.completed",
            payment_attempt=payment,
            livemode=False,
            processing_status="failed",
            payload_digest="b" * 64,
            received_at=CUTOFF - timedelta(days=100),
            processed_at=CUTOFF - timedelta(days=100),
        )
        expired = token(user, expires_at=CUTOFF - timedelta(days=1))
        active = token(user, expires_at=NOW + timedelta(days=1))
        db.add_all([listing, order, payment, webhook, expired, active])
        db.flush()
        protected = {
            User: user.id,
            Category: category.id,
            Product: product.id,
            ProductVariant: variant.id,
            Listing: listing.id,
            Order: order.id,
            PaymentAttempt: payment.id,
            StripeWebhookEvent: webhook.id,
        }
        expired_id = expired.id
        active_id = active.id

    try:
        with SessionLocal.begin() as db:
            result = delete_refresh_token_batch(db, cutoff=CUTOFF, batch_size=100)
        assert result.deleted_count == 1
        with SessionLocal() as db:
            assert db.get(RefreshToken, expired_id) is None
            assert db.get(RefreshToken, active_id) is not None
            for model, row_id in protected.items():
                assert db.get(model, row_id) is not None
            assert db.scalar(select(func.count()).select_from(StripeWebhookEvent).where(StripeWebhookEvent.id == protected[StripeWebhookEvent])) == 1
    finally:
        with SessionLocal.begin() as db:
            db.execute(delete(StripeWebhookEvent).where(StripeWebhookEvent.id == protected[StripeWebhookEvent]))
            db.execute(delete(PaymentAttempt).where(PaymentAttempt.id == protected[PaymentAttempt]))
            db.execute(delete(Order).where(Order.id == protected[Order]))
            db.execute(delete(Listing).where(Listing.id == protected[Listing]))
            db.execute(delete(ProductVariant).where(ProductVariant.id == protected[ProductVariant]))
            db.execute(delete(Product).where(Product.id == protected[Product]))
            db.execute(delete(Category).where(Category.id == protected[Category]))
            db.execute(delete(RefreshToken).where(RefreshToken.user_id == protected[User]))
            db.execute(delete(User).where(User.id == protected[User]))
        engine.dispose()
