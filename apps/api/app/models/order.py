from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Order(TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("status IN ('pending_payment', 'confirmed', 'cancelled')", name="status_known"),
        CheckConstraint("payment_status IN ('unpaid', 'paid', 'failed', 'refunded')", name="payment_status_known"),
        CheckConstraint("subtotal_cents >= 0", name="subtotal_cents_non_negative"),
        CheckConstraint("shipping_cents >= 0", name="shipping_cents_non_negative"),
        CheckConstraint("tax_cents >= 0", name="tax_cents_non_negative"),
        CheckConstraint("total_cents >= 0", name="total_cents_non_negative"),
        UniqueConstraint("user_id", "idempotency_key", name="uq_orders_user_id_idempotency_key"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="confirmed", server_default="confirmed")
    payment_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unpaid", server_default="unpaid")
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    subtotal_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    shipping_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    tax_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(320), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(320), nullable=False)
    contact_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str] = mapped_column(String(32), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reservation_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    inventory_released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="orders")
    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="OrderItem.created_at",
    )
    payment_attempts = relationship(
        "PaymentAttempt",
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PaymentAttempt.created_at",
    )


class OrderItem(TimestampMixin, Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price_cents >= 0", name="unit_price_cents_non_negative"),
        CheckConstraint("line_total_cents >= 0", name="line_total_cents_non_negative"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    listing_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("listings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_variant_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    product_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    variant_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    variant_sku: Mapped[str | None] = mapped_column(String(128), nullable=True)
    variant_size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    variant_color: Mapped[str | None] = mapped_column(String(128), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    order = relationship("Order", back_populates="items")
    listing = relationship("Listing", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")
    product_variant = relationship("ProductVariant", back_populates="order_items")


class PaymentAttempt(TimestampMixin, Base):
    __tablename__ = "payment_attempts"
    __table_args__ = (
        CheckConstraint("provider IN ('stripe')", name="provider_known"),
        CheckConstraint(
            "status IN ('initializing', 'open', 'processing', 'paid', 'failed', 'expired', 'cancelled')",
            name="status_known",
        ),
        CheckConstraint("amount_cents > 0", name="amount_cents_positive"),
        UniqueConstraint("provider_session_id", name="uq_payment_attempts_provider_session_id"),
        UniqueConstraint("provider_payment_intent_id", name="uq_payment_attempts_provider_payment_intent_id"),
        UniqueConstraint("provider_idempotency_key", name="uq_payment_attempts_provider_idempotency_key"),
        UniqueConstraint("correlation_id", name="uq_payment_attempts_correlation_id"),
        Index("ix_payment_attempts_order_id_status", "order_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False, default="stripe", server_default="stripe")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="initializing", server_default="initializing")
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    provider_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_livemode: Mapped[bool] = mapped_column(Boolean, nullable=False)
    hosted_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(String(255), nullable=True)

    order = relationship("Order", back_populates="payment_attempts")
    webhook_events = relationship("StripeWebhookEvent", back_populates="payment_attempt")


class StripeWebhookEvent(TimestampMixin, Base):
    __tablename__ = "stripe_webhook_events"
    __table_args__ = (
        CheckConstraint("processing_status IN ('received', 'processed', 'ignored', 'failed')", name="processing_status_known"),
        UniqueConstraint("stripe_event_id", name="uq_stripe_webhook_events_stripe_event_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    stripe_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider_object_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    payment_attempt_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("payment_attempts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    livemode: Mapped[bool] = mapped_column(Boolean, nullable=False)
    processing_status: Mapped[str] = mapped_column(String(32), nullable=False, default="received", server_default="received")
    payload_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    error_summary: Mapped[str | None] = mapped_column(String(255), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now().astimezone(),
        server_default=func.now(),
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    payment_attempt = relationship("PaymentAttempt", back_populates="webhook_events")
