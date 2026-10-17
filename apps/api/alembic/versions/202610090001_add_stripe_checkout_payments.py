"""add stripe checkout payments

Revision ID: 202610090001
Revises: 202610080001
Create Date: 2026-10-09 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202610090001"
down_revision: Union[str, None] = "202610080001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("reservation_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("inventory_released_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        op.f("ix_orders_reservation_expires_at"),
        "orders",
        ["reservation_expires_at"],
        unique=False,
    )

    op.create_table(
        "payment_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=32), server_default="stripe", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="initializing", nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("provider_session_id", sa.String(length=255), nullable=True),
        sa.Column("provider_payment_intent_id", sa.String(length=255), nullable=True),
        sa.Column("provider_livemode", sa.Boolean(), nullable=False),
        sa.Column("hosted_url", sa.Text(), nullable=True),
        sa.Column("provider_idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(length=100), nullable=True),
        sa.Column("failure_message", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("provider IN ('stripe')", name=op.f("ck_payment_attempts_provider_known")),
        sa.CheckConstraint(
            "status IN ('initializing', 'open', 'processing', 'paid', 'failed', 'expired', 'cancelled')",
            name=op.f("ck_payment_attempts_status_known"),
        ),
        sa.CheckConstraint("amount_cents > 0", name=op.f("ck_payment_attempts_amount_cents_positive")),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name=op.f("fk_payment_attempts_order_id_orders"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_payment_attempts")),
        sa.UniqueConstraint("provider_session_id", name="uq_payment_attempts_provider_session_id"),
        sa.UniqueConstraint("provider_payment_intent_id", name="uq_payment_attempts_provider_payment_intent_id"),
        sa.UniqueConstraint("provider_idempotency_key", name="uq_payment_attempts_provider_idempotency_key"),
        sa.UniqueConstraint("correlation_id", name="uq_payment_attempts_correlation_id"),
    )
    op.create_index(op.f("ix_payment_attempts_order_id"), "payment_attempts", ["order_id"], unique=False)
    op.create_index(op.f("ix_payment_attempts_expires_at"), "payment_attempts", ["expires_at"], unique=False)
    op.create_index("ix_payment_attempts_order_id_status", "payment_attempts", ["order_id", "status"], unique=False)

    op.create_table(
        "stripe_webhook_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("stripe_event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=255), nullable=False),
        sa.Column("provider_object_id", sa.String(length=255), nullable=True),
        sa.Column("payment_attempt_id", sa.Uuid(), nullable=True),
        sa.Column("livemode", sa.Boolean(), nullable=False),
        sa.Column("processing_status", sa.String(length=32), server_default="received", nullable=False),
        sa.Column("payload_digest", sa.String(length=64), nullable=False),
        sa.Column("error_summary", sa.String(length=255), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "processing_status IN ('received', 'processed', 'ignored', 'failed')",
            name=op.f("ck_stripe_webhook_events_processing_status_known"),
        ),
        sa.ForeignKeyConstraint(
            ["payment_attempt_id"],
            ["payment_attempts.id"],
            name=op.f("fk_stripe_webhook_events_payment_attempt_id_payment_attempts"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stripe_webhook_events")),
        sa.UniqueConstraint("stripe_event_id", name="uq_stripe_webhook_events_stripe_event_id"),
    )
    op.create_index(op.f("ix_stripe_webhook_events_event_type"), "stripe_webhook_events", ["event_type"], unique=False)
    op.create_index(
        op.f("ix_stripe_webhook_events_provider_object_id"),
        "stripe_webhook_events",
        ["provider_object_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_stripe_webhook_events_payment_attempt_id"),
        "stripe_webhook_events",
        ["payment_attempt_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_stripe_webhook_events_payment_attempt_id"), table_name="stripe_webhook_events")
    op.drop_index(op.f("ix_stripe_webhook_events_provider_object_id"), table_name="stripe_webhook_events")
    op.drop_index(op.f("ix_stripe_webhook_events_event_type"), table_name="stripe_webhook_events")
    op.drop_table("stripe_webhook_events")

    op.drop_index("ix_payment_attempts_order_id_status", table_name="payment_attempts")
    op.drop_index(op.f("ix_payment_attempts_expires_at"), table_name="payment_attempts")
    op.drop_index(op.f("ix_payment_attempts_order_id"), table_name="payment_attempts")
    op.drop_table("payment_attempts")

    op.drop_index(op.f("ix_orders_reservation_expires_at"), table_name="orders")
    op.drop_column("orders", "inventory_released_at")
    op.drop_column("orders", "reservation_expires_at")
