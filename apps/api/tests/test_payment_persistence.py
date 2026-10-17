from sqlalchemy import Boolean, DateTime, Integer
from pathlib import Path

from app.db.base import Base
from app.models import Order, PaymentAttempt, StripeWebhookEvent


def constraint_sql(table_name: str) -> set[str]:
    return {
        str(constraint.sqltext)
        for constraint in Base.metadata.tables[table_name].constraints
        if constraint.__class__.__name__ == "CheckConstraint"
    }


def unique_columns(table_name: str) -> set[tuple[str, ...]]:
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in Base.metadata.tables[table_name].constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }


def test_payment_attempt_model_has_lifecycle_money_provider_and_order_contract() -> None:
    table = PaymentAttempt.__table__
    assert {
        "order_id",
        "provider",
        "status",
        "amount_cents",
        "currency",
        "provider_session_id",
        "provider_payment_intent_id",
        "provider_livemode",
        "hosted_url",
        "provider_idempotency_key",
        "correlation_id",
        "expires_at",
        "completed_at",
        "failure_code",
    }.issubset(table.c.keys())
    assert isinstance(table.c.amount_cents.type, Integer)
    assert isinstance(table.c.provider_livemode.type, Boolean)
    assert isinstance(table.c.expires_at.type, DateTime)
    assert table.c.order_id.nullable is False
    assert next(iter(table.c.order_id.foreign_keys)).ondelete == "CASCADE"
    assert "amount_cents > 0" in constraint_sql("payment_attempts")
    assert "provider_session_id" in {columns[0] for columns in unique_columns("payment_attempts")}
    assert "provider_payment_intent_id" in {columns[0] for columns in unique_columns("payment_attempts")}
    assert "provider_idempotency_key" in {columns[0] for columns in unique_columns("payment_attempts")}
    assert {"order_id", "expires_at"}.issubset({column.name for index in table.indexes for column in index.columns})


def test_webhook_event_model_deduplicates_and_stores_only_safe_metadata() -> None:
    table = StripeWebhookEvent.__table__
    assert {
        "stripe_event_id",
        "event_type",
        "provider_object_id",
        "payment_attempt_id",
        "livemode",
        "processing_status",
        "payload_digest",
        "error_summary",
        "received_at",
        "processed_at",
    }.issubset(table.c.keys())
    assert {"payload", "raw_payload", "card", "card_data"}.isdisjoint(table.c.keys())
    assert ("stripe_event_id",) in unique_columns("stripe_webhook_events")
    assert next(iter(table.c.payment_attempt_id.foreign_keys)).ondelete == "SET NULL"
    assert {"event_type", "provider_object_id", "payment_attempt_id"}.issubset(
        {column.name for index in table.indexes for column in index.columns}
    )


def test_order_has_nullable_reservation_fields_and_payment_relationship() -> None:
    table = Order.__table__
    assert table.c.reservation_expires_at.nullable is True
    assert table.c.inventory_released_at.nullable is True
    assert "payment_attempts" in Order.__mapper__.relationships


def test_payment_migration_declares_deterministic_upgrade_and_downgrade() -> None:
    source = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "202610090001_add_stripe_checkout_payments.py"
    ).read_text()
    assert 'down_revision: Union[str, None] = "202610080001"' in source
    assert 'op.create_table(\n        "payment_attempts"' in source
    assert 'op.create_table(\n        "stripe_webhook_events"' in source
    assert 'op.add_column("orders", sa.Column("reservation_expires_at"' in source
    assert 'op.add_column("orders", sa.Column("inventory_released_at"' in source
    assert 'op.drop_table("stripe_webhook_events")' in source
    assert 'op.drop_table("payment_attempts")' in source
    assert 'op.drop_column("orders", "reservation_expires_at")' in source
