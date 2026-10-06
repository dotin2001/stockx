"""add customer admin messages

Revision ID: 202609250001
Revises: 202609240001
Create Date: 2026-09-25 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "202609250001"
down_revision: Union[str, None] = "202609240001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_admin_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("sender_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], name=op.f("fk_customer_admin_messages_sender_user_id_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_customer_admin_messages")),
    )
    op.create_index(op.f("ix_customer_admin_messages_sender_user_id"), "customer_admin_messages", ["sender_user_id"], unique=False)
    op.create_index(op.f("ix_customer_admin_messages_is_read"), "customer_admin_messages", ["is_read"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_customer_admin_messages_is_read"), table_name="customer_admin_messages")
    op.drop_index(op.f("ix_customer_admin_messages_sender_user_id"), table_name="customer_admin_messages")
    op.drop_table("customer_admin_messages")
