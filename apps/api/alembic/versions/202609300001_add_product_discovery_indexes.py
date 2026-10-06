"""add product discovery indexes

Revision ID: 202609300001
Revises: 202609270001
Create Date: 2026-09-30 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "202609300001"
down_revision: Union[str, None] = "202609270001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f("ix_products_brand"), "products", ["brand"], unique=False)
    op.create_index(op.f("ix_product_variants_size"), "product_variants", ["size"], unique=False)
    op.create_index(op.f("ix_listings_price_cents"), "listings", ["price_cents"], unique=False)
    op.create_index(op.f("ix_listings_available_quantity"), "listings", ["available_quantity"], unique=False)
    op.create_index(op.f("ix_listings_status"), "listings", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_listings_status"), table_name="listings")
    op.drop_index(op.f("ix_listings_available_quantity"), table_name="listings")
    op.drop_index(op.f("ix_listings_price_cents"), table_name="listings")
    op.drop_index(op.f("ix_product_variants_size"), table_name="product_variants")
    op.drop_index(op.f("ix_products_brand"), table_name="products")
