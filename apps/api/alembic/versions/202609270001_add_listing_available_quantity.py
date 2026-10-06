"""add listing available quantity

Revision ID: 202609270001
Revises: 202609260001
Create Date: 2026-09-27 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "202609270001"
down_revision: Union[str, None] = "202609260001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "listings",
        sa.Column("available_quantity", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_listings_available_quantity_non_negative"),
        "listings",
        "available_quantity >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_listings_available_quantity_non_negative"), "listings", type_="check")
    op.drop_column("listings", "available_quantity")
