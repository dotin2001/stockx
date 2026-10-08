from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
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

    user = relationship("User", back_populates="orders")
    items = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="OrderItem.created_at",
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
