from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Event
from uuid import uuid4

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import sessionmaker

from app.models import Category, Listing, Product, ProductVariant, User
from tests.postgres_support import create_postgres_test_engine, require_postgres_url


PREVIOUS_REVISION = "202610290001"
ROOT = Path(__file__).resolve().parents[1]
TIMEOUT_SECONDS = 15


@pytest.fixture()
def lowest_ask_data():
    engine = create_postgres_test_engine()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    suffix = uuid4().hex
    with SessionLocal() as db:
        category = Category(name=f"Lowest ask {suffix}", slug=f"lowest-ask-{suffix}")
        seller = User(
            name="Lowest Ask Seller",
            email=f"lowest-ask-{suffix}@example.test",
            password_hash="unused",
            is_admin=True,
        )
        first = Product(category=category, name="First Lowest Ask", slug=f"lowest-ask-first-{suffix}")
        second = Product(category=category, name="Second Lowest Ask", slug=f"lowest-ask-second-{suffix}")
        listings = [
            Listing(user=seller, product=first, price_cents=12000, available_quantity=2, currency="USD", status="active"),
            Listing(user=seller, product=first, price_cents=15000, available_quantity=2, currency="USD", status="active"),
            Listing(user=seller, product=first, price_cents=5000, available_quantity=2, currency="EUR", status="active"),
            Listing(user=seller, product=second, price_cents=22000, available_quantity=2, currency="USD", status="active"),
            Listing(user=seller, product=second, price_cents=24000, available_quantity=2, currency="USD", status="active"),
        ]
        db.add_all(listings)
        db.commit()
        ids = {
            "suffix": suffix,
            "category": category.id,
            "seller": seller.id,
            "products": [first.id, second.id],
            "listings": [listing.id for listing in listings],
        }

    try:
        yield engine, SessionLocal, ids
    finally:
        with SessionLocal() as db:
            db.execute(delete(Listing).where(Listing.product_id.in_(ids["products"])))
            db.execute(delete(ProductVariant).where(ProductVariant.product_id.in_(ids["products"])))
            db.execute(delete(Product).where(Product.id.in_(ids["products"])))
            db.execute(delete(Category).where(Category.id == ids["category"]))
            db.execute(delete(User).where(User.id == ids["seller"]))
            db.commit()
        engine.dispose()


def _lowest(connection, product_id):
    return connection.scalar(
        text("SELECT lowest_ask_cents FROM products WHERE id = :product_id"),
        {"product_id": product_id},
    )


def test_direct_sql_mutations_and_multi_row_updates_maintain_projection(lowest_ask_data) -> None:
    engine, _SessionLocal, ids = lowest_ask_data
    first, second = ids["products"]
    low, high, eur, second_low, second_high = ids["listings"]

    with engine.begin() as connection:
        assert _lowest(connection, first) == 12000
        assert _lowest(connection, second) == 22000

        connection.execute(text("UPDATE listings SET price_cents = 11000 WHERE id = :id"), {"id": high})
        assert _lowest(connection, first) == 11000

        connection.execute(text("UPDATE listings SET status = 'sold' WHERE id = :id"), {"id": high})
        assert _lowest(connection, first) == 12000

        connection.execute(text("UPDATE listings SET available_quantity = 0 WHERE id = :id"), {"id": low})
        assert _lowest(connection, first) is None

        connection.execute(text("UPDATE listings SET currency = 'USD' WHERE id = :id"), {"id": eur})
        assert _lowest(connection, first) == 5000

        connection.execute(text("UPDATE listings SET product_id = :second WHERE id = :id"), {"second": second, "id": eur})
        assert _lowest(connection, first) is None
        assert _lowest(connection, second) == 5000

        connection.execute(text("DELETE FROM listings WHERE id = :id"), {"id": eur})
        assert _lowest(connection, second) == 22000

        connection.execute(
            text("UPDATE listings SET available_quantity = 0 WHERE id IN (:first, :second)"),
            {"first": second_low, "second": second_high},
        )
        assert _lowest(connection, second) is None


@pytest.mark.parametrize(
    ("first_sql", "second_sql", "expected"),
    [
        ("UPDATE listings SET price_cents = 9000 WHERE id = :id", "UPDATE listings SET price_cents = 8000 WHERE id = :id", 8000),
        ("UPDATE listings SET status = 'sold' WHERE id = :id", "UPDATE listings SET available_quantity = 0 WHERE id = :id", None),
    ],
)
def test_concurrent_same_product_changes_converge(lowest_ask_data, first_sql: str, second_sql: str, expected: int | None) -> None:
    engine, _SessionLocal, ids = lowest_ask_data
    barrier = Barrier(2, timeout=TIMEOUT_SECONDS)

    def mutate(sql: str, listing_id) -> None:
        barrier.wait()
        with engine.begin() as connection:
            connection.execute(text(sql), {"id": listing_id})

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(mutate, first_sql, ids["listings"][0]),
            executor.submit(mutate, second_sql, ids["listings"][1]),
        ]
        for future in futures:
            future.result(timeout=TIMEOUT_SECONDS)

    with engine.connect() as connection:
        assert _lowest(connection, ids["products"][0]) == expected


def test_concurrent_delete_and_update_converge(lowest_ask_data) -> None:
    engine, _SessionLocal, ids = lowest_ask_data
    barrier = Barrier(2, timeout=TIMEOUT_SECONDS)

    def delete_low() -> None:
        barrier.wait()
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM listings WHERE id = :id"), {"id": ids["listings"][0]})

    def reprice_high() -> None:
        barrier.wait()
        with engine.begin() as connection:
            connection.execute(text("UPDATE listings SET price_cents = 13000 WHERE id = :id"), {"id": ids["listings"][1]})

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(delete_low), executor.submit(reprice_high)]
        for future in futures:
            future.result(timeout=TIMEOUT_SECONDS)

    with engine.connect() as connection:
        assert _lowest(connection, ids["products"][0]) == 13000


def test_product_reassignment_locks_products_in_stable_order(lowest_ask_data) -> None:
    engine, _SessionLocal, ids = lowest_ask_data
    first, second = ids["products"]
    barrier = Barrier(2, timeout=TIMEOUT_SECONDS)

    def move(listing_id, target_product) -> None:
        barrier.wait()
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE listings SET product_id = :target WHERE id = :id"),
                {"target": target_product, "id": listing_id},
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(move, ids["listings"][0], second),
            executor.submit(move, ids["listings"][3], first),
        ]
        for future in futures:
            future.result(timeout=TIMEOUT_SECONDS)

    with engine.connect() as connection:
        assert _lowest(connection, first) == 15000
        assert _lowest(connection, second) == 12000


def test_different_products_do_not_share_a_global_lock(lowest_ask_data) -> None:
    engine, _SessionLocal, ids = lowest_ask_data
    locked = Event()
    release = Event()

    def hold_first_product() -> None:
        with engine.begin() as connection:
            connection.execute(text("SELECT id FROM products WHERE id = :id FOR UPDATE"), {"id": ids["products"][0]})
            locked.set()
            assert release.wait(TIMEOUT_SECONDS)

    def mutate_second_product() -> None:
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE listings SET price_cents = 21000 WHERE id = :id"),
                {"id": ids["listings"][3]},
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        holder = executor.submit(hold_first_product)
        assert locked.wait(TIMEOUT_SECONDS)
        other = executor.submit(mutate_second_product)
        other.result(timeout=TIMEOUT_SECONDS)
        release.set()
        holder.result(timeout=TIMEOUT_SECONDS)

    with engine.connect() as connection:
        assert _lowest(connection, ids["products"][1]) == 21000


def test_migration_downgrade_reupgrade_preserves_business_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    url = require_postgres_url()
    monkeypatch.setenv("ALEMBIC_DATABASE_URL", url)
    config = Config(str(ROOT / "alembic.ini"))
    engine = create_postgres_test_engine()
    command.upgrade(config, "head")
    try:
        with engine.connect() as connection:
            before = connection.execute(
                text(
                    "SELECT (SELECT count(*) FROM products), "
                    "(SELECT count(*) FROM product_variants), "
                    "(SELECT count(*) FROM listings), "
                    "(SELECT count(*) FROM orders), "
                    "(SELECT coalesce(sum(available_quantity), 0) FROM listings)"
                )
            ).one()

        command.downgrade(config, PREVIOUS_REVISION)
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM information_schema.columns WHERE table_name = 'products' AND column_name = 'lowest_ask_cents'")) == 1
        command.upgrade(config, "head")

        with engine.connect() as connection:
            after = connection.execute(
                text(
                    "SELECT (SELECT count(*) FROM products), "
                    "(SELECT count(*) FROM product_variants), "
                    "(SELECT count(*) FROM listings), "
                    "(SELECT count(*) FROM orders), "
                    "(SELECT coalesce(sum(available_quantity), 0) FROM listings)"
                )
            ).one()
            trigger_count = connection.scalar(
                text("SELECT count(*) FROM pg_trigger WHERE tgname LIKE 'trg_listings_lowest_ask%' AND NOT tgisinternal")
            )
        assert after == before
        assert trigger_count == 4
    finally:
        command.upgrade(config, "head")
        engine.dispose()
