from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.errors import APIError
from app.models import Category, Listing, Product, ProductVariant, User
from app.schemas.product import ProductVariantCreate, ProductVariantUpdate
from app.services import admin_products, auth, listings
from tests.postgres_support import create_postgres_test_engine


BARRIER_TIMEOUT_SECONDS = 10
WORKER_TIMEOUT_SECONDS = 20


@pytest.fixture()
def postgres_identity_data():
    engine = create_postgres_test_engine()
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    suffix = uuid4().hex
    with SessionLocal() as db:
        category = Category(name=f"Identity {suffix}", slug=f"identity-{suffix}")
        sentinel = Category(name=f"Sentinel {suffix}", slug=f"sentinel-{suffix}")
        product = Product(category=category, name="Identity Product", slug=f"identity-product-{suffix}", total_sold=0)
        actor = User(
            name="Concurrency Admin",
            email=f"concurrency-admin-{suffix}@example.test",
            password_hash="unused",
            is_admin=True,
            is_supreme_admin=True,
        )
        sufficient = Listing(
            user=actor,
            product=product,
            price_cents=10000,
            available_quantity=3,
            currency="USD",
            status="active",
        )
        oversubscribed = Listing(
            user=actor,
            product=product,
            price_cents=10000,
            available_quantity=1,
            currency="USD",
            status="active",
        )
        first_update = ProductVariant(product=product, size="U1", sku=f"UPDATE-A-{suffix}")
        second_update = ProductVariant(product=product, size="U2", sku=f"UPDATE-B-{suffix}")
        db.add_all([sentinel, sufficient, oversubscribed, first_update, second_update])
        db.commit()
        ids = {
            "suffix": suffix,
            "category": category.id,
            "sentinel": sentinel.id,
            "product": product.id,
            "actor": actor.id,
            "sufficient": sufficient.id,
            "oversubscribed": oversubscribed.id,
            "update_variants": [first_update.id, second_update.id],
        }

    try:
        yield SessionLocal, ids
    finally:
        with SessionLocal() as db:
            db.execute(delete(Listing).where(Listing.product_id == ids["product"]))
            db.execute(delete(ProductVariant).where(ProductVariant.product_id == ids["product"]))
            db.execute(delete(Product).where(Product.id == ids["product"]))
            db.execute(delete(Category).where(Category.id == ids["category"]))
            db.execute(delete(User).where(User.email.like(f"%{ids['suffix']}%")))
            db.commit()
            assert db.get(Category, ids["sentinel"]) is not None
            db.execute(delete(Category).where(Category.id == ids["sentinel"]))
            db.commit()
        engine.dispose()


def _run_workers(function, values):
    with ThreadPoolExecutor(max_workers=len(values)) as executor:
        futures = [executor.submit(function, value) for value in values]
        return [future.result(timeout=WORKER_TIMEOUT_SECONDS) for future in futures]


def test_concurrent_equivalent_email_registration_has_one_winner(
    postgres_identity_data,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    SessionLocal, ids = postgres_identity_data
    barrier = Barrier(2, timeout=BARRIER_TIMEOUT_SECONDS)
    original_lookup = auth.get_user_by_email

    def synchronized_lookup(db: Session, email: str):
        result = original_lookup(db, email)
        barrier.wait()
        return result

    monkeypatch.setattr(auth, "get_user_by_email", synchronized_lookup)
    email = f"race-{ids['suffix']}@example.test"

    def attempt(candidate: str):
        with SessionLocal() as db:
            try:
                user = auth.register_user(db, name="Race", email=candidate, password="password123")
                db.commit()
                return "success", user.id
            except APIError as exc:
                db.rollback()
                return exc.code, None

    results = _run_workers(attempt, [f"  {email.upper()}  ", email])
    assert [result[0] for result in results].count("success") == 1
    assert [result[0] for result in results].count("email_exists") == 1
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(User).where(User.email == email)) == 1


def test_concurrent_equivalent_sku_create_and_update_have_stable_conflicts(
    postgres_identity_data,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    SessionLocal, ids = postgres_identity_data
    create_barrier = Barrier(2, timeout=BARRIER_TIMEOUT_SECONDS)
    original_check = admin_products._ensure_unique_sku

    def synchronized_create_check(db: Session, sku: str | None, *, excluding_variant_id=None):
        original_check(db, sku, excluding_variant_id=excluding_variant_id)
        create_barrier.wait()

    monkeypatch.setattr(admin_products, "_ensure_unique_sku", synchronized_create_check)
    target = f"RACE-SKU-{ids['suffix']}"

    def create_attempt(candidate: str):
        with SessionLocal() as db:
            try:
                variant = admin_products.create_variant(
                    db,
                    product_id=ids["product"],
                    payload=ProductVariantCreate(size=candidate[-1], sku=candidate),
                )
                db.commit()
                return "success", variant.id
            except APIError as exc:
                db.rollback()
                return exc.code, None

    create_results = _run_workers(create_attempt, [f"  {target.lower()}  ", target])
    assert [result[0] for result in create_results].count("success") == 1
    assert [result[0] for result in create_results].count("variant_sku_exists") == 1

    update_barrier = Barrier(2, timeout=BARRIER_TIMEOUT_SECONDS)

    def synchronized_update_check(db: Session, sku: str | None, *, excluding_variant_id=None):
        original_check(db, sku, excluding_variant_id=excluding_variant_id)
        update_barrier.wait()

    monkeypatch.setattr(admin_products, "_ensure_unique_sku", synchronized_update_check)
    update_target = f"UPDATE-RACE-{ids['suffix']}"

    def update_attempt(variant_id):
        with SessionLocal() as db:
            try:
                variant = admin_products.update_variant(
                    db,
                    variant_id=variant_id,
                    payload=ProductVariantUpdate(sku=update_target),
                )
                db.commit()
                return "success", variant.id
            except APIError as exc:
                db.rollback()
                return exc.code, variant_id

    update_results = _run_workers(update_attempt, ids["update_variants"])
    assert [result[0] for result in update_results].count("success") == 1
    assert [result[0] for result in update_results].count("variant_sku_exists") == 1
    with SessionLocal() as db:
        variants = list(db.scalars(select(ProductVariant).where(ProductVariant.id.in_(ids["update_variants"]))).all())
        assert sum(variant.sku == update_target for variant in variants) == 1
        assert sum(variant.sku in {f"UPDATE-A-{ids['suffix']}", f"UPDATE-B-{ids['suffix']}"} for variant in variants) == 1


@pytest.mark.parametrize(
    ("listing_key", "adjustments", "expected_successes", "expected_quantity"),
    [
        ("sufficient", [-1, -1], 2, 1),
        ("oversubscribed", [-1, -1], 1, 0),
    ],
)
def test_concurrent_inventory_reductions_are_atomic(
    postgres_identity_data,
    listing_key: str,
    adjustments: list[int],
    expected_successes: int,
    expected_quantity: int,
) -> None:
    SessionLocal, ids = postgres_identity_data
    barrier = Barrier(2, timeout=BARRIER_TIMEOUT_SECONDS)

    def attempt(adjustment: int):
        with SessionLocal() as db:
            actor = db.get(User, ids["actor"])
            assert actor is not None
            barrier.wait()
            try:
                updated = listings.adjust_managed_listing_quantity(
                    db,
                    listing_id=ids[listing_key],
                    adjustment=adjustment,
                    actor=actor,
                )
                db.commit()
                return "success", updated.available_quantity
            except APIError as exc:
                db.rollback()
                return exc.code, None

    results = _run_workers(attempt, adjustments)
    assert [result[0] for result in results].count("success") == expected_successes
    assert all(result[0] in {"success", "inventory_quantity_below_zero"} for result in results)
    with SessionLocal() as db:
        listing = db.get(Listing, ids[listing_key])
        assert listing is not None
        assert listing.available_quantity == expected_quantity
        assert listing.available_quantity >= 0
