"""enforce normalized email and SKU identity integrity

Revision ID: 202610290001
Revises: 202610090001
Create Date: 2026-10-29 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202610290001"
down_revision: Union[str, None] = "202610090001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _first_mapping(connection, statement: str):
    return connection.execute(sa.text(statement)).mappings().first()


def _require_collision_free_data() -> None:
    connection = op.get_bind()
    email_collision = _first_mapping(
        connection,
        """
        SELECT lower(btrim(email)) AS identity, count(*) AS row_count
        FROM users
        GROUP BY lower(btrim(email))
        HAVING count(*) > 1
        ORDER BY min(id::text)
        LIMIT 1
        """,
    )
    if email_collision is not None:
        raise RuntimeError(
            "normalized email collisions must be remediated before upgrade "
            f"(conflicting rows: {email_collision['row_count']})"
        )

    sku_collision = _first_mapping(
        connection,
        """
        SELECT lower(btrim(sku)) AS identity, count(*) AS row_count
        FROM product_variants
        WHERE sku IS NOT NULL AND btrim(sku) <> ''
        GROUP BY lower(btrim(sku))
        HAVING count(*) > 1
        ORDER BY min(id::text)
        LIMIT 1
        """,
    )
    if sku_collision is not None:
        raise RuntimeError(
            "normalized SKU collisions must be remediated before upgrade "
            f"(conflicting rows: {sku_collision['row_count']})"
        )

    invalid_email = _first_mapping(
        connection,
        """
        SELECT id::text AS id
        FROM users
        WHERE email <> lower(btrim(email)) OR btrim(email) = ''
        ORDER BY id
        LIMIT 1
        """,
    )
    if invalid_email is not None:
        raise RuntimeError(
            "noncanonical email rows must be remediated before upgrade "
            f"(example user id: {invalid_email['id']})"
        )

    invalid_sku = _first_mapping(
        connection,
        """
        SELECT id::text AS id
        FROM product_variants
        WHERE sku IS NOT NULL AND (sku <> btrim(sku) OR btrim(sku) = '')
        ORDER BY id
        LIMIT 1
        """,
    )
    if invalid_sku is not None:
        raise RuntimeError(
            "noncanonical SKU rows must be remediated before upgrade "
            f"(example variant id: {invalid_sku['id']})"
        )


def upgrade() -> None:
    _require_collision_free_data()
    op.create_check_constraint(
        op.f("ck_users_email_canonical"),
        "users",
        "email = lower(btrim(email)) AND btrim(email) <> ''",
    )
    op.create_index(
        "uq_users_email_normalized",
        "users",
        [sa.text("lower(btrim(email))")],
        unique=True,
    )
    op.create_check_constraint(
        op.f("ck_product_variants_sku_canonical"),
        "product_variants",
        "sku IS NULL OR (sku = btrim(sku) AND btrim(sku) <> '')",
    )
    op.create_index(
        "uq_product_variants_sku_normalized",
        "product_variants",
        [sa.text("lower(btrim(sku))")],
        unique=True,
        postgresql_where=sa.text("sku IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_product_variants_sku_normalized", table_name="product_variants")
    op.drop_constraint(op.f("ck_product_variants_sku_canonical"), "product_variants", type_="check")
    op.drop_index("uq_users_email_normalized", table_name="users")
    op.drop_constraint(op.f("ck_users_email_canonical"), "users", type_="check")
