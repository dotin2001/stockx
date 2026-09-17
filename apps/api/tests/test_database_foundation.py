from sqlalchemy import Boolean, Float, Integer

from app.db.base import Base
from app.db.seed import CATEGORIES, PRODUCTS


def test_foundation_tables_are_declared() -> None:
    assert {
        "users",
        "refresh_tokens",
        "categories",
        "products",
        "product_variants",
        "listings",
        "watchlist_items",
    }.issubset(Base.metadata.tables.keys())


def test_users_have_boolean_admin_flag_and_no_text_access_level() -> None:
    users = Base.metadata.tables["users"]

    assert "is_admin" in users.c
    assert isinstance(users.c.is_admin.type, Boolean)
    assert users.c.is_admin.nullable is False
    assert "role" not in users.c
    assert "access_level" not in users.c


def test_money_columns_use_integer_cents() -> None:
    products = Base.metadata.tables["products"]
    listings = Base.metadata.tables["listings"]

    assert isinstance(products.c.lowest_ask_cents.type, Integer)
    assert isinstance(listings.c.price_cents.type, Integer)

    for table in Base.metadata.tables.values():
        for column in table.c:
            assert not isinstance(column.type, Float)


def test_seed_data_has_stable_unique_slugs() -> None:
    category_slugs = [category.slug for category in CATEGORIES]
    product_slugs = [product.slug for product in PRODUCTS]

    assert {"sneakers", "streetwear", "collectibles"}.issubset(category_slugs)
    assert len(category_slugs) == len(set(category_slugs))
    assert len(product_slugs) == len(set(product_slugs))
    assert all(product.lowest_ask_cents is None or product.lowest_ask_cents >= 0 for product in PRODUCTS)

