"""add checkout orders

Revision ID: 202610080001
Revises: 202610040001
Create Date: 2026-10-08 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202610080001"
down_revision: Union[str, None] = "202610040001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_number", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="confirmed", nullable=False),
        sa.Column("payment_status", sa.String(length=32), server_default="unpaid", nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("subtotal_cents", sa.Integer(), nullable=False),
        sa.Column("shipping_cents", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tax_cents", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_cents", sa.Integer(), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=False),
        sa.Column("customer_email", sa.String(length=320), nullable=False),
        sa.Column("recipient_name", sa.String(length=255), nullable=False),
        sa.Column("contact_email", sa.String(length=320), nullable=False),
        sa.Column("contact_phone", sa.String(length=32), nullable=False),
        sa.Column("address_line1", sa.String(length=255), nullable=False),
        sa.Column("address_line2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("state", sa.String(length=120), nullable=True),
        sa.Column("postal_code", sa.String(length=32), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('pending_payment', 'confirmed', 'cancelled')", name=op.f("ck_orders_status_known")),
        sa.CheckConstraint("payment_status IN ('unpaid', 'paid', 'failed', 'refunded')", name=op.f("ck_orders_payment_status_known")),
        sa.CheckConstraint("subtotal_cents >= 0", name=op.f("ck_orders_subtotal_cents_non_negative")),
        sa.CheckConstraint("shipping_cents >= 0", name=op.f("ck_orders_shipping_cents_non_negative")),
        sa.CheckConstraint("tax_cents >= 0", name=op.f("ck_orders_tax_cents_non_negative")),
        sa.CheckConstraint("total_cents >= 0", name=op.f("ck_orders_total_cents_non_negative")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_orders_user_id_users"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
        sa.UniqueConstraint("order_number", name=op.f("uq_orders_order_number")),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_orders_user_id_idempotency_key"),
    )
    op.create_index(op.f("ix_orders_order_number"), "orders", ["order_number"], unique=True)
    op.create_index(op.f("ix_orders_user_id"), "orders", ["user_id"], unique=False)

    op.create_table(
        "order_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=True),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column("product_variant_id", sa.Uuid(), nullable=True),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("product_slug", sa.String(length=255), nullable=False),
        sa.Column("product_image_url", sa.Text(), nullable=True),
        sa.Column("variant_label", sa.String(length=255), nullable=True),
        sa.Column("variant_sku", sa.String(length=128), nullable=True),
        sa.Column("variant_size", sa.String(length=64), nullable=True),
        sa.Column("variant_color", sa.String(length=128), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False),
        sa.Column("line_total_cents", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_order_items_quantity_positive")),
        sa.CheckConstraint("unit_price_cents >= 0", name=op.f("ck_order_items_unit_price_cents_non_negative")),
        sa.CheckConstraint("line_total_cents >= 0", name=op.f("ck_order_items_line_total_cents_non_negative")),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], name=op.f("fk_order_items_listing_id_listings"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], name=op.f("fk_order_items_order_id_orders"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], name=op.f("fk_order_items_product_id_products"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_variant_id"], ["product_variants.id"], name=op.f("fk_order_items_product_variant_id_product_variants"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_items")),
    )
    op.create_index(op.f("ix_order_items_listing_id"), "order_items", ["listing_id"], unique=False)
    op.create_index(op.f("ix_order_items_order_id"), "order_items", ["order_id"], unique=False)
    op.create_index(op.f("ix_order_items_product_id"), "order_items", ["product_id"], unique=False)
    op.create_index(op.f("ix_order_items_product_variant_id"), "order_items", ["product_variant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_order_items_product_variant_id"), table_name="order_items")
    op.drop_index(op.f("ix_order_items_product_id"), table_name="order_items")
    op.drop_index(op.f("ix_order_items_order_id"), table_name="order_items")
    op.drop_index(op.f("ix_order_items_listing_id"), table_name="order_items")
    op.drop_table("order_items")
    op.drop_index(op.f("ix_orders_user_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_order_number"), table_name="orders")
    op.drop_table("orders")
