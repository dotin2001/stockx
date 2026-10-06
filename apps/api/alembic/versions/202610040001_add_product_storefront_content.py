"""add product storefront content

Revision ID: 202610040001
Revises: 202609300001
Create Date: 2026-10-04 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "202610040001"
down_revision: Union[str, None] = "202609300001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "products",
        sa.Column("feature_bullets", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "products",
        sa.Column("detail_rows", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "products",
        sa.Column("gallery_images", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("products", "gallery_images")
    op.drop_column("products", "detail_rows")
    op.drop_column("products", "feature_bullets")
