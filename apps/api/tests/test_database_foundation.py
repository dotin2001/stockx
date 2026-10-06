from collections import Counter

import pytest
from sqlalchemy import Boolean, DateTime, Float, Integer, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.seed import (
    CATEGORIES,
    PRODUCTS,
    SEED_INVENTORY_QUANTITY,
    SEED_SKU_PREFIX,
    SeedInventoryOwnerError,
    parse_args,
    upsert_categories,
    upsert_products,
    upsert_seed_inventory,
)
from app.models import Listing, Product, ProductVariant, User


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
    assert "is_supreme_admin" in users.c
    assert isinstance(users.c.is_supreme_admin.type, Boolean)
    assert users.c.is_supreme_admin.nullable is False
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


def test_listings_have_non_negative_available_quantity() -> None:
    listings = Base.metadata.tables["listings"]

    assert "available_quantity" in listings.c
    assert isinstance(listings.c.available_quantity.type, Integer)
    assert listings.c.available_quantity.nullable is False

    check_constraints = {
        str(constraint.sqltext)
        for constraint in listings.constraints
        if constraint.__class__.__name__ == "CheckConstraint"
    }
    assert "available_quantity >= 0" in check_constraints


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


def test_seed_data_has_five_valid_products_per_supported_category() -> None:
    counts = Counter(product.category_slug for product in PRODUCTS)

    assert counts == {"sneakers": 5, "streetwear": 5, "collectibles": 5}
    assert all(product.name.strip() for product in PRODUCTS)
    assert all(product.image_url and product.image_url.startswith("http") for product in PRODUCTS)
    assert all(product.lowest_ask_cents is not None and product.lowest_ask_cents > 0 for product in PRODUCTS)


def test_seed_purchase_option_metadata_is_unique() -> None:
    seed_skus = [product.seed_sku for product in PRODUCTS]

    assert len(seed_skus) == 15
    assert len(seed_skus) == len(set(seed_skus))
    assert all(sku.startswith(SEED_SKU_PREFIX) for sku in seed_skus)
    assert {product.seed_size for product in PRODUCTS} == {"10", "M", "One Size"}


def test_seed_cli_accepts_optional_inventory_owner() -> None:
    assert parse_args([]).inventory_owner_email is None
    assert parse_args(["--inventory-owner-email", "Admin@Example.com"]).inventory_owner_email == "Admin@Example.com"


def prepare_seed_catalog(session: Session) -> None:
    upsert_categories(session)
    upsert_products(session)
    session.flush()


def test_inventory_seed_requires_an_existing_admin(db_session: Session) -> None:
    prepare_seed_catalog(db_session)
    customer = User(name="Customer", email="customer@example.com", password_hash="not-used")
    db_session.add(customer)
    db_session.flush()

    with pytest.raises(SeedInventoryOwnerError, match="not found"):
        upsert_seed_inventory(db_session, owner_email="missing@example.com")
    with pytest.raises(SeedInventoryOwnerError, match="must be an admin"):
        upsert_seed_inventory(db_session, owner_email=" CUSTOMER@EXAMPLE.COM ")

    assert db_session.scalar(select(func.count()).select_from(Listing)) == 0


def test_inventory_seed_is_idempotent_and_preserves_unrelated_inventory(db_session: Session) -> None:
    prepare_seed_catalog(db_session)
    owner = User(name="Store Admin", email="admin@example.com", password_hash="not-used", is_admin=True)
    db_session.add(owner)
    db_session.flush()

    seeded_product = db_session.scalar(select(Product).where(Product.slug == PRODUCTS[0].slug))
    assert seeded_product is not None
    unrelated_variant = ProductVariant(product_id=seeded_product.id, size="11", color="Red", sku="ADMIN-CUSTOM-SKU")
    db_session.add(unrelated_variant)
    db_session.flush()
    unrelated_listing = Listing(
        user_id=owner.id,
        product_id=seeded_product.id,
        product_variant_id=unrelated_variant.id,
        price_cents=99900,
        available_quantity=3,
        currency="USD",
        status="active",
    )
    db_session.add(unrelated_listing)
    db_session.flush()

    upsert_seed_inventory(db_session, owner_email=" ADMIN@EXAMPLE.COM ")
    db_session.flush()
    upsert_seed_inventory(db_session, owner_email="admin@example.com")
    db_session.flush()

    variants = list(db_session.scalars(select(ProductVariant).where(ProductVariant.sku.startswith(SEED_SKU_PREFIX))).all())
    variant_ids = [variant.id for variant in variants]
    listings = list(
        db_session.scalars(
            select(Listing).where(Listing.user_id == owner.id, Listing.product_variant_id.in_(variant_ids))
        ).all()
    )

    assert len(variants) == 15
    assert len(listings) == 15
    assert all(listing.available_quantity == SEED_INVENTORY_QUANTITY for listing in listings)
    assert all(listing.currency == "USD" and listing.status == "active" for listing in listings)
    assert {listing.price_cents for listing in listings} == {
        product.lowest_ask_cents for product in PRODUCTS
    }
    assert db_session.get(Listing, unrelated_listing.id) is unrelated_listing
    assert unrelated_listing.available_quantity == 3
    assert unrelated_listing.price_cents == 99900
