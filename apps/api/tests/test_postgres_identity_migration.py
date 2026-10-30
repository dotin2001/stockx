from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
import sqlalchemy as sa
from sqlalchemy import inspect

from tests.postgres_support import create_postgres_test_engine, require_postgres_url


PREVIOUS_REVISION = "202610090001"
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def migration_database(monkeypatch: pytest.MonkeyPatch):
    url = require_postgres_url()
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", url)
    config = Config(str(ROOT / "alembic.ini"))
    engine = create_postgres_test_engine()
    suffix = uuid4().hex
    command.upgrade(config, "head")
    try:
        yield config, engine, suffix
    finally:
        with engine.begin() as connection:
            connection.execute(
                sa.text(
                    "DELETE FROM product_variants WHERE product_id IN "
                    "(SELECT id FROM products WHERE slug LIKE :pattern)"
                ),
                {"pattern": f"identity-migration-{suffix}%"},
            )
            connection.execute(
                sa.text("DELETE FROM products WHERE slug LIKE :pattern"),
                {"pattern": f"identity-migration-{suffix}%"},
            )
            connection.execute(
                sa.text("DELETE FROM categories WHERE slug LIKE :pattern"),
                {"pattern": f"identity-migration-{suffix}%"},
            )
            connection.execute(
                sa.text("DELETE FROM users WHERE lower(email) LIKE :pattern"),
                {"pattern": f"%{suffix}%"},
            )
        command.upgrade(config, "head")
        engine.dispose()


def _insert_product(connection, suffix: str):
    category_id = uuid4()
    product_id = uuid4()
    connection.execute(
        sa.text("INSERT INTO categories (id, name, slug) VALUES (:id, :name, :slug)"),
        {"id": category_id, "name": "Migration Identity", "slug": f"identity-migration-{suffix}"},
    )
    connection.execute(
        sa.text(
            "INSERT INTO products (id, category_id, name, slug, total_sold) "
            "VALUES (:id, :category_id, :name, :slug, 0)"
        ),
        {
            "id": product_id,
            "category_id": category_id,
            "name": "Migration Identity",
            "slug": f"identity-migration-{suffix}",
        },
    )
    return category_id, product_id


def test_migration_rejects_email_collisions_without_changing_rows(migration_database) -> None:
    config, engine, suffix = migration_database
    command.downgrade(config, PREVIOUS_REVISION)
    first_id, second_id = uuid4(), uuid4()
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO users (id, name, email, password_hash) VALUES "
                "(:first_id, 'First', :first_email, 'unused'), "
                "(:second_id, 'Second', :second_email, 'unused')"
            ),
            {
                "first_id": first_id,
                "second_id": second_id,
                "first_email": f"collision-{suffix}@example.test",
                "second_email": f"COLLISION-{suffix}@example.test",
            },
        )

    with pytest.raises(RuntimeError, match="normalized email collisions"):
        command.upgrade(config, "head")

    with engine.connect() as connection:
        rows = connection.execute(
            sa.text("SELECT id, email FROM users WHERE id IN (:first_id, :second_id) ORDER BY email"),
            {"first_id": first_id, "second_id": second_id},
        ).all()
    assert len(rows) == 2
    assert {row.email for row in rows} == {
        f"collision-{suffix}@example.test",
        f"COLLISION-{suffix}@example.test",
    }


def test_migration_rejects_sku_collisions_without_changing_rows(migration_database) -> None:
    config, engine, suffix = migration_database
    command.downgrade(config, PREVIOUS_REVISION)
    first_id, second_id = uuid4(), uuid4()
    with engine.begin() as connection:
        _category_id, product_id = _insert_product(connection, suffix)
        connection.execute(
            sa.text(
                "INSERT INTO product_variants (id, product_id, size, sku) VALUES "
                "(:first_id, :product_id, '1', :first_sku), "
                "(:second_id, :product_id, '2', :second_sku)"
            ),
            {
                "first_id": first_id,
                "second_id": second_id,
                "product_id": product_id,
                "first_sku": f"SKU-{suffix}",
                "second_sku": f" sku-{suffix} ",
            },
        )

    with pytest.raises(RuntimeError, match="normalized SKU collisions"):
        command.upgrade(config, "head")

    with engine.connect() as connection:
        rows = connection.execute(
            sa.text("SELECT id, sku FROM product_variants WHERE id IN (:first_id, :second_id)"),
            {"first_id": first_id, "second_id": second_id},
        ).all()
    assert len(rows) == 2
    assert {row.sku for row in rows} == {f"SKU-{suffix}", f" sku-{suffix} "}


@pytest.mark.parametrize(
    ("kind", "expected_message"),
    [("email", "noncanonical email rows"), ("sku", "noncanonical SKU rows")],
)
def test_migration_rejects_noncanonical_rows(migration_database, kind: str, expected_message: str) -> None:
    config, engine, suffix = migration_database
    command.downgrade(config, PREVIOUS_REVISION)
    with engine.begin() as connection:
        if kind == "email":
            connection.execute(
                sa.text("INSERT INTO users (id, name, email, password_hash) VALUES (:id, 'Invalid', :email, 'unused')"),
                {"id": uuid4(), "email": f" Invalid-{suffix}@example.test "},
            )
        else:
            _category_id, product_id = _insert_product(connection, suffix)
            connection.execute(
                sa.text("INSERT INTO product_variants (id, product_id, size, sku) VALUES (:id, :product_id, '1', '   ')"),
                {"id": uuid4(), "product_id": product_id},
            )

    with pytest.raises(RuntimeError, match=expected_message):
        command.upgrade(config, "head")


def test_migration_lifecycle_preserves_records_and_installs_named_objects(migration_database) -> None:
    config, engine, suffix = migration_database
    user_id, variant_id = uuid4(), uuid4()
    with engine.begin() as connection:
        connection.execute(
            sa.text("INSERT INTO users (id, name, email, password_hash) VALUES (:id, 'Lifecycle', :email, 'unused')"),
            {"id": user_id, "email": f"lifecycle-{suffix}@example.test"},
        )
        _category_id, product_id = _insert_product(connection, suffix)
        connection.execute(
            sa.text("INSERT INTO product_variants (id, product_id, size, sku) VALUES (:id, :product_id, '1', :sku)"),
            {"id": variant_id, "product_id": product_id, "sku": f"LIFECYCLE-{suffix}"},
        )

    command.downgrade(config, PREVIOUS_REVISION)
    command.upgrade(config, "head")

    with engine.connect() as connection:
        assert connection.scalar(sa.text("SELECT count(*) FROM users WHERE id = :id"), {"id": user_id}) == 1
        assert connection.scalar(sa.text("SELECT count(*) FROM product_variants WHERE id = :id"), {"id": variant_id}) == 1

    inspector = inspect(engine)
    user_checks = {item["name"] for item in inspector.get_check_constraints("users")}
    variant_checks = {item["name"] for item in inspector.get_check_constraints("product_variants")}
    user_indexes = {item["name"] for item in inspector.get_indexes("users")}
    variant_indexes = {item["name"] for item in inspector.get_indexes("product_variants")}
    assert "ck_users_email_canonical" in user_checks
    assert "ck_product_variants_sku_canonical" in variant_checks
    assert "uq_users_email_normalized" in user_indexes
    assert "uq_product_variants_sku_normalized" in variant_indexes
