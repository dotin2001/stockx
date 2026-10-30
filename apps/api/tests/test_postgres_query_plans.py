from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.postgres_support import assert_explicit_test_database, create_postgres_test_engine


CANDIDATE_INDEXES = {
    "ix_listings_qualifying_product_price": (
        "CREATE INDEX ix_listings_qualifying_product_price ON listings (product_id, price_cents, id) "
        "WHERE status = 'active' AND available_quantity > 0 AND currency = 'USD'"
    ),
    "ix_product_variants_product_size": (
        "CREATE INDEX ix_product_variants_product_size ON product_variants (product_id, size)"
    ),
    "ix_listings_status_created_at_id": (
        "CREATE INDEX ix_listings_status_created_at_id ON listings (status, created_at DESC, id)"
    ),
}


QUERY_CASES = {
    "text_search": (
        "SELECT id FROM products WHERE archived_at IS NULL AND "
        "(name ILIKE :pattern OR slug ILIKE :pattern OR brand ILIKE :pattern OR description ILIKE :pattern) "
        "ORDER BY id",
        {"pattern": "%plan-fixture%"},
    ),
    "category": (
        "SELECT id FROM products WHERE archived_at IS NULL AND category_id = :category_id ORDER BY id",
        {},
    ),
    "brand": (
        "SELECT id FROM products WHERE archived_at IS NULL AND brand = :brand ORDER BY id",
        {"brand": "Plan Brand 3"},
    ),
    "size": (
        "SELECT product.id FROM products AS product WHERE product.archived_at IS NULL AND EXISTS ("
        "SELECT 1 FROM product_variants AS variant WHERE variant.product_id = product.id AND variant.size = :size"
        ") ORDER BY product.id",
        {"size": "10"},
    ),
    "price_availability": (
        "SELECT id FROM products WHERE archived_at IS NULL AND lowest_ask_cents BETWEEN :minimum AND :maximum "
        "ORDER BY id",
        {"minimum": 10000, "maximum": 20000},
    ),
    "lowest_listing": (
        "SELECT product_id, min(price_cents) FROM listings WHERE status = 'active' "
        "AND available_quantity > 0 AND currency = 'USD' GROUP BY product_id ORDER BY product_id",
        {},
    ),
    "price_sort": (
        "SELECT id FROM products WHERE archived_at IS NULL ORDER BY lowest_ask_cents NULLS LAST, name, id LIMIT 50",
        {},
    ),
    "admin_listings": (
        "SELECT id FROM listings WHERE status = :status ORDER BY created_at DESC, id LIMIT 50",
        {"status": "active"},
    ),
}


def _index_definitions(connection):
    return dict(
        connection.execute(
            text(
                "SELECT indexname, indexdef FROM pg_indexes "
                "WHERE schemaname = current_schema() AND tablename IN ('products', 'product_variants', 'listings') "
                "ORDER BY indexname"
            )
        ).all()
    )


def _capture(connection, category_id):
    evidence = {}
    for name, (sql, base_parameters) in QUERY_CASES.items():
        parameters = {**base_parameters}
        if name == "category":
            parameters["category_id"] = category_id
        rows = connection.execute(text(sql), parameters).all()
        plan = connection.execute(text(f"EXPLAIN (FORMAT JSON) {sql}"), parameters).scalar_one()
        assert isinstance(plan, list) and plan and "Plan" in plan[0]
        evidence[name] = {"parameters": parameters, "rows": rows, "plan": plan}
    return evidence


def test_representative_plans_results_indexes_and_scoped_cleanup() -> None:
    engine = create_postgres_test_engine()
    assert_explicit_test_database(engine)
    suffix = uuid4().hex
    category_slug = f"plan-fixture-{suffix}"
    seller_email = f"plan-fixture-{suffix}@example.test"
    category_id = seller_id = None
    product_ids = []

    try:
        with engine.begin() as connection:
            category_id = connection.scalar(
                text("INSERT INTO categories (name, slug) VALUES (:name, :slug) RETURNING id"),
                {"name": f"Plan Fixture {suffix}", "slug": category_slug},
            )
            seller_id = connection.scalar(
                text(
                    "INSERT INTO users (name, email, password_hash, is_admin) "
                    "VALUES ('Plan Fixture', :email, 'unused', true) RETURNING id"
                ),
                {"email": seller_email},
            )
            product_ids = list(
                connection.scalars(
                    text(
                        "INSERT INTO products (category_id, name, slug, brand, description, total_sold) "
                        "SELECT :category_id, 'plan-fixture product ' || value, "
                        ":slug_prefix || value, 'Plan Brand ' || (value % 8), 'plan-fixture description', value "
                        "FROM generate_series(1, 160) AS value RETURNING id"
                    ),
                    {"category_id": category_id, "slug_prefix": f"plan-fixture-{suffix}-"},
                ).all()
            )
            connection.execute(
                text(
                    "INSERT INTO product_variants (product_id, size, sku) "
                    "SELECT id, CASE WHEN total_sold % 2 = 0 THEN '10' ELSE '9' END, "
                    "'PLAN-' || :suffix || '-' || total_sold FROM products WHERE id = ANY(:product_ids)"
                ),
                {"suffix": suffix, "product_ids": product_ids},
            )
            connection.execute(
                text(
                    "INSERT INTO listings (user_id, product_id, price_cents, available_quantity, currency, status) "
                    "SELECT :seller_id, id, 9000 + (total_sold * 100), "
                    "CASE WHEN total_sold % 11 = 0 THEN 0 ELSE 3 END, "
                    "CASE WHEN total_sold % 13 = 0 THEN 'EUR' ELSE 'USD' END, "
                    "CASE WHEN total_sold % 7 = 0 THEN 'sold' ELSE 'active' END "
                    "FROM products WHERE id = ANY(:product_ids)"
                ),
                {"seller_id": seller_id, "product_ids": product_ids},
            )

        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                installed = _index_definitions(connection)
                for name in CANDIDATE_INDEXES:
                    assert name in installed
                    connection.execute(text(f"DROP INDEX {name}"))
                connection.execute(text("ANALYZE products"))
                connection.execute(text("ANALYZE product_variants"))
                connection.execute(text("ANALYZE listings"))
                baseline_definitions = _index_definitions(connection)
                baseline = _capture(connection, category_id)

                for statement in CANDIDATE_INDEXES.values():
                    connection.execute(text(statement))
                connection.execute(text("ANALYZE product_variants"))
                connection.execute(text("ANALYZE listings"))
                final_definitions = _index_definitions(connection)
                final = _capture(connection, category_id)

                assert {name: item["rows"] for name, item in final.items()} == {
                    name: item["rows"] for name, item in baseline.items()
                }
                assert all(name not in baseline_definitions for name in CANDIDATE_INDEXES)
                assert all(name in final_definitions for name in CANDIDATE_INDEXES)
                assert not any("trgm" in name.lower() for name in final_definitions)
                assert "ix_listings_product_id" in baseline_definitions
                assert "ix_product_variants_product_id" in baseline_definitions
                assert "ix_product_variants_size" in baseline_definitions
                assert "ix_listings_status" in baseline_definitions
            finally:
                transaction.rollback()
    finally:
        if product_ids and category_id and seller_id:
            with engine.begin() as connection:
                connection.execute(text("DELETE FROM listings WHERE product_id = ANY(:ids)"), {"ids": product_ids})
                connection.execute(text("DELETE FROM product_variants WHERE product_id = ANY(:ids)"), {"ids": product_ids})
                connection.execute(text("DELETE FROM products WHERE id = ANY(:ids)"), {"ids": product_ids})
                connection.execute(text("DELETE FROM categories WHERE id = :id"), {"id": category_id})
                connection.execute(text("DELETE FROM users WHERE id = :id"), {"id": seller_id})
                assert connection.scalar(text("SELECT count(*) FROM products WHERE slug LIKE :pattern"), {"pattern": f"plan-fixture-{suffix}-%"}) == 0
        engine.dispose()
