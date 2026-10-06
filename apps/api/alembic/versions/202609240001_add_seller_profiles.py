"""add seller profiles

Revision ID: 202609240001
Revises: 202609200001
Create Date: 2026-09-24 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202609240001"
down_revision: Union[str, None] = "202609200001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "seller_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("phone_number", sa.String(length=32), nullable=False),
        sa.Column("address_line1", sa.String(length=255), nullable=False),
        sa.Column("address_line2", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=False),
        sa.Column("state", sa.String(length=128), nullable=True),
        sa.Column("postal_code", sa.String(length=32), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_seller_profiles_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_seller_profiles")),
        sa.UniqueConstraint("user_id", name=op.f("uq_seller_profiles_user_id")),
    )
    op.create_index(op.f("ix_seller_profiles_user_id"), "seller_profiles", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_seller_profiles_user_id"), table_name="seller_profiles")
    op.drop_table("seller_profiles")
