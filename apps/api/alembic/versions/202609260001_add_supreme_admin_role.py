"""add supreme admin role

Revision ID: 202609260001
Revises: 202609250001
Create Date: 2026-09-26 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202609260001"
down_revision: Union[str, None] = "202609250001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_supreme_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "is_supreme_admin")
