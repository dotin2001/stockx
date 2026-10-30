from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.core.identity import normalize_email, normalize_sku
from app.models import Product, ProductVariant, User
from app.schemas.product import ProductVariantCreate, ProductVariantUpdate
from app.services import admin_products, auth


def test_email_normalization_is_shared_and_defensive(db_session: Session) -> None:
    user = auth.register_user(
        db_session,
        name="Normalized Buyer",
        email="  Normalized.Buyer@Example.COM  ",
        password="password123",
    )
    db_session.commit()

    assert user.email == "normalized.buyer@example.com"
    assert auth.get_user_by_email(db_session, " NORMALIZED.BUYER@example.com ") is user
    assert normalize_email(" Test@Example.COM ") == "test@example.com"
    with pytest.raises(ValueError, match="must not be blank"):
        normalize_email("   ")


def test_concurrent_style_email_constraint_conflict_uses_stable_error(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing = auth.register_user(
        db_session,
        name="Existing",
        email="identity@example.com",
        password="password123",
    )
    db_session.commit()

    monkeypatch.setattr(auth, "get_user_by_email", lambda *_args, **_kwargs: None)
    with pytest.raises(APIError) as conflict:
        auth.register_user(
            db_session,
            name="Racing Request",
            email=" IDENTITY@example.com ",
            password="password123",
        )

    assert conflict.value.status_code == 409
    assert conflict.value.code == "email_exists"
    assert db_session.scalar(select(User).where(User.id == existing.id)) is not None


def test_sku_normalization_create_update_nulls_and_conflicts(db_session: Session) -> None:
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))
    assert product is not None

    first = admin_products.create_variant(
        db_session,
        product_id=product.id,
        payload=ProductVariantCreate(size="8", sku="  Global-SKU  "),
    )
    first_id = first.id
    blank = admin_products.create_variant(
        db_session,
        product_id=product.id,
        payload=ProductVariantCreate(size="8.5", sku="   "),
    )
    absent = admin_products.create_variant(
        db_session,
        product_id=product.id,
        payload=ProductVariantCreate(size="9", sku=None),
    )
    db_session.commit()

    assert first.sku == "Global-SKU"
    assert blank.sku is None
    assert absent.sku is None
    assert normalize_sku("  SKU-1 ") == "SKU-1"
    assert normalize_sku(" ") is None

    with pytest.raises(APIError) as create_conflict:
        admin_products.create_variant(
            db_session,
            product_id=product.id,
            payload=ProductVariantCreate(size="9.5", sku=" global-sku "),
        )
    assert create_conflict.value.code == "variant_sku_exists"

    preserved = admin_products.create_variant(
        db_session,
        product_id=product.id,
        payload=ProductVariantCreate(size="10", sku=f"OTHER-{uuid4().hex}"),
    )
    db_session.commit()
    preserved_id = preserved.id
    preserved_sku = preserved.sku
    with pytest.raises(APIError) as update_conflict:
        admin_products.update_variant(
            db_session,
            variant_id=preserved_id,
            payload=ProductVariantUpdate(sku=" GLOBAL-SKU "),
        )
    assert update_conflict.value.code == "variant_sku_exists"
    assert db_session.get(ProductVariant, preserved_id).sku == preserved_sku

    cleared = admin_products.update_variant(
        db_session,
        variant_id=first_id,
        payload=ProductVariantUpdate(sku="  "),
    )
    db_session.commit()
    assert cleared.sku is None


def test_omitted_variant_update_fields_remain_unchanged(db_session: Session) -> None:
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))
    assert product is not None
    variant = admin_products.create_variant(
        db_session,
        product_id=product.id,
        payload=ProductVariantCreate(size="11", color="Blue", sku=f"OMITTED-{uuid4().hex}"),
    )
    db_session.commit()
    original_sku = variant.sku

    updated = admin_products.update_variant(
        db_session,
        variant_id=variant.id,
        payload=ProductVariantUpdate(color="Red"),
    )
    db_session.commit()

    assert updated.color == "Red"
    assert updated.sku == original_sku


def test_unknown_email_integrity_errors_propagate(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unknown = IntegrityError("statement", {}, Exception("unrelated database failure"))
    monkeypatch.setattr(db_session, "flush", lambda: (_ for _ in ()).throw(unknown))

    with pytest.raises(IntegrityError) as raised:
        auth.register_user(
            db_session,
            name="Unknown Error",
            email="unknown-error@example.test",
            password="password123",
        )

    assert raised.value is unknown


def test_unknown_sku_integrity_errors_propagate(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))
    assert product is not None
    unknown = IntegrityError("statement", {}, Exception("unrelated database failure"))
    monkeypatch.setattr(db_session, "flush", lambda: (_ for _ in ()).throw(unknown))

    with pytest.raises(IntegrityError) as raised:
        admin_products.create_variant(
            db_session,
            product_id=product.id,
            payload=ProductVariantCreate(size="12", sku=f"UNKNOWN-{uuid4().hex}"),
        )

    assert raised.value is unknown
