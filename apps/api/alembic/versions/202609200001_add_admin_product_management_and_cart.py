"""add admin product management and cart

Revision ID: 202609200001
Revises: 202609170001
Create Date: 2026-09-20 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202609200001"
down_revision: Union[str, None] = "202609170001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("products", sa.Column("archived_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        op.f("fk_products_archived_by_user_id_users"),
        "products",
        "users",
        ["archived_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_products_archived_at"), "products", ["archived_at"], unique=False)

    op.create_table(
        "cart_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("listing_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("quantity > 0", name=op.f("ck_cart_items_quantity_positive")),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], name=op.f("fk_cart_items_listing_id_listings"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_cart_items_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cart_items")),
        sa.UniqueConstraint("user_id", "listing_id", name="uq_cart_items_user_id_listing_id"),
    )
    op.create_index(op.f("ix_cart_items_listing_id"), "cart_items", ["listing_id"], unique=False)
    op.create_index(op.f("ix_cart_items_user_id"), "cart_items", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_cart_items_user_id"), table_name="cart_items")
    op.drop_index(op.f("ix_cart_items_listing_id"), table_name="cart_items")
    op.drop_table("cart_items")

    op.drop_index(op.f("ix_products_archived_at"), table_name="products")
    op.drop_constraint(op.f("fk_products_archived_by_user_id_users"), "products", type_="foreignkey")
    op.drop_column("products", "archived_by_user_id")
    op.drop_column("products", "archived_at")
