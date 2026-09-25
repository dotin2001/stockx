from sqlalchemy import Boolean, DateTime, Float, Integer

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
        "cart_items",
        "seller_profiles",
        "customer_admin_messages",
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


def test_products_have_archive_metadata() -> None:
    products = Base.metadata.tables["products"]

    assert "archived_at" in products.c
    assert "archived_by_user_id" in products.c
    assert isinstance(products.c.archived_at.type, DateTime)
    assert products.c.archived_at.nullable is True
    assert products.c.archived_by_user_id.nullable is True


def test_cart_items_are_user_listing_scoped_with_positive_quantity() -> None:
    cart_items = Base.metadata.tables["cart_items"]

    assert {"user_id", "listing_id", "quantity"}.issubset(cart_items.c.keys())
    assert isinstance(cart_items.c.quantity.type, Integer)
    assert cart_items.c.quantity.nullable is False

    unique_constraints = {
        tuple(column.name for column in constraint.columns)
        for constraint in cart_items.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("user_id", "listing_id") in unique_constraints

    check_constraints = {
        str(constraint.sqltext)
        for constraint in cart_items.constraints
        if constraint.__class__.__name__ == "CheckConstraint"
    }
    assert "quantity > 0" in check_constraints


def test_seller_profiles_are_user_scoped_contact_records() -> None:
    seller_profiles = Base.metadata.tables["seller_profiles"]

    assert {"user_id", "phone_number", "address_line1", "city", "country"}.issubset(seller_profiles.c.keys())
    assert seller_profiles.c.user_id.nullable is False
    assert seller_profiles.c.phone_number.nullable is False
    assert seller_profiles.c.address_line1.nullable is False
    assert seller_profiles.c.city.nullable is False
    assert seller_profiles.c.country.nullable is False

    unique_constraints = {
        tuple(column.name for column in constraint.columns)
        for constraint in seller_profiles.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("user_id",) in unique_constraints


def test_customer_admin_messages_are_sender_scoped_support_records() -> None:
    messages = Base.metadata.tables["customer_admin_messages"]

    assert {"sender_user_id", "subject", "body", "is_read", "read_at"}.issubset(messages.c.keys())
    assert messages.c.sender_user_id.nullable is False
    assert messages.c.subject.nullable is False
    assert messages.c.body.nullable is False
    assert messages.c.is_read.nullable is False
    assert messages.c.read_at.nullable is True
    assert isinstance(messages.c.is_read.type, Boolean)
    assert isinstance(messages.c.read_at.type, DateTime)


def test_seed_data_has_stable_unique_slugs() -> None:
    category_slugs = [category.slug for category in CATEGORIES]
    product_slugs = [product.slug for product in PRODUCTS]

    assert {"sneakers", "streetwear", "collectibles"}.issubset(category_slugs)
    assert len(category_slugs) == len(set(category_slugs))
    assert len(product_slugs) == len(set(product_slugs))
    assert all(product.lowest_ask_cents is None or product.lowest_ask_cents >= 0 for product in PRODUCTS)
