from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password, verify_password
from app.models import Category, Listing, Product, RefreshToken, User, WatchlistItem
from app.schemas.product import ProductSummary
from app.services import admin_products
from app.services import auth as auth_service
from app.services.admin_bootstrap import AdminPromotionError, promote_existing_user
from app.services.integrity import matches_integrity_target


def register_user(client: TestClient, email: str = "buyer@example.com") -> tuple[str, dict]:
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Buyer", "email": email, "password": "password123"},
    )
    assert response.status_code == 201
    body = response.json()
    return body["access_token"], body


def admin_headers(client: TestClient, db_session: Session, email: str = "admin@example.com") -> dict[str, str]:
    access_token, _body = register_user(client, email=email)
    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    user.is_admin = True
    db_session.commit()
    return {"Authorization": f"Bearer {access_token}"}


def test_health_and_versioned_catalog_route(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}

    response = client.get("/api/v1/categories")

    assert response.status_code == 200
    assert {category["slug"] for category in response.json()} == {"sneakers", "streetwear"}


def test_settings_parse_environment_values(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://api:api@localhost:5433/api")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "5")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "9")
    monkeypatch.setenv("REFRESH_COOKIE_NAME", "refresh_test")
    monkeypatch.setenv("REFRESH_COOKIE_SECURE", "true")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001")
    monkeypatch.setenv("POSTGRES_USER", "stockx")
    monkeypatch.setenv("POSTGRES_PASSWORD", "stockx")
    monkeypatch.setenv("POSTGRES_DB", "stockx")
    monkeypatch.setenv("POSTGRES_PORT", "5432")

    settings = Settings()

    assert settings.database_url == "postgresql+psycopg://api:api@localhost:5433/api"
    assert settings.secret_key == "test-secret"
    assert settings.access_token_expire_minutes == 5
    assert settings.refresh_token_expire_days == 9
    assert settings.refresh_cookie_name == "refresh_test"
    assert settings.refresh_cookie_secure is True
    assert settings.cors_origins == ["http://localhost:3000", "http://localhost:3001"]


def test_error_shapes_for_validation_and_not_found(client: TestClient) -> None:
    validation = client.get("/api/v1/search?q=")
    missing = client.get("/api/v1/products/not-real")

    assert validation.status_code == 422
    assert validation.json()["error"]["code"] == "validation_error"
    assert missing.status_code == 404
    assert missing.json() == {"error": {"code": "product_not_found", "message": "Product was not found."}}


def test_password_hashing_never_stores_raw_password(db_session: Session) -> None:
    password_hash = hash_password("password123")
    user = auth_service.register_user(
        db_session,
        name="Hash Test",
        email="hash@example.com",
        password="password123",
    )

    assert password_hash != "password123"
    assert verify_password("password123", password_hash)
    assert not verify_password("wrong-password", password_hash)
    assert user.password_hash != "password123"


def test_admin_promotion_service_preserves_auth_data(db_session: Session) -> None:
    user = auth_service.register_user(
        db_session,
        name="Promote Me",
        email="promote@example.com",
        password="password123",
    )
    _record, _raw_token = auth_service.create_refresh_token_record(db_session, user)
    password_hash = user.password_hash
    refresh_token_ids = {token.id for token in user.refresh_tokens}

    promoted = promote_existing_user(db_session, email="  PROMOTE@example.com ")
    db_session.commit()

    assert promoted.id == user.id
    assert promoted.email == "promote@example.com"
    assert promoted.is_admin is True
    assert promoted.password_hash == password_hash
    assert {token.id for token in promoted.refresh_tokens} == refresh_token_ids

    promoted_again = promote_existing_user(db_session, email="promote@example.com")
    db_session.commit()
    assert promoted_again.id == user.id
    assert promoted_again.is_admin is True
    assert promoted_again.password_hash == password_hash
    assert len(db_session.scalars(select(User).where(User.email == "promote@example.com")).all()) == 1

    with pytest.raises(AdminPromotionError):
        promote_existing_user(db_session, email="missing@example.com")


def test_schema_serialization_for_product_summary(db_session: Session) -> None:
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))

    summary = ProductSummary.model_validate(product)

    assert summary.slug == "jordan-1-retro-high-test"
    assert summary.category.slug == "sneakers"
    assert summary.lowest_ask_cents == 24300


def test_auth_register_login_me_refresh_and_logout(client: TestClient, db_session: Session) -> None:
    access_token, body = register_user(client)

    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "buyer@example.com"
    assert "stockx_refresh" in client.cookies

    user = db_session.scalar(select(User).where(User.email == "buyer@example.com"))
    assert user is not None
    assert user.password_hash != "password123"

    duplicate = client.post(
        "/api/v1/auth/register",
        json={"name": "Buyer", "email": "buyer@example.com", "password": "password123"},
    )
    assert duplicate.status_code == 409

    invalid_login = client.post(
        "/api/v1/auth/login",
        json={"email": "buyer@example.com", "password": "wrong-password"},
    )
    assert invalid_login.status_code == 401
    assert invalid_login.json()["error"]["code"] == "invalid_credentials"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "buyer@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    assert "stockx_refresh" in client.cookies

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "buyer@example.com"

    old_refresh = client.cookies.get("stockx_refresh")
    refresh = client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 200
    assert refresh.json()["access_token"] != access_token
    assert client.cookies.get("stockx_refresh") != old_refresh

    replay = client.post("/api/v1/auth/refresh", cookies={"stockx_refresh": old_refresh})
    assert replay.status_code == 401

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204
    assert "stockx_refresh" not in client.cookies

    revoked_count = len(db_session.scalars(select(RefreshToken).where(RefreshToken.revoked_at.is_not(None))).all())
    assert revoked_count >= 2


def test_catalog_product_category_detail_and_search(client: TestClient) -> None:
    products = client.get("/api/v1/products?limit=1&offset=0")
    assert products.status_code == 200
    assert products.json()["limit"] == 1
    assert products.json()["total"] == 2
    assert products.json()["items"][0]["category"]["slug"] in {"sneakers", "streetwear"}

    category_products = client.get("/api/v1/categories/sneakers/products")
    assert category_products.status_code == 200
    assert {item["category"]["slug"] for item in category_products.json()["items"]} == {"sneakers"}

    missing_category = client.get("/api/v1/categories/collectibles/products")
    assert missing_category.status_code == 404

    detail = client.get("/api/v1/products/jordan-1-retro-high-test")
    assert detail.status_code == 200
    assert detail.json()["variants"][0]["size"] == "10"
    assert detail.json()["lowest_active_listing"] is None

    search = client.get("/api/v1/search?q=jordan")
    assert search.status_code == 200
    assert search.json()["items"][0]["slug"] == "jordan-1-retro-high-test"


def test_admin_product_management_flow(client: TestClient, db_session: Session) -> None:
    category = db_session.scalar(select(Category).where(Category.slug == "sneakers"))
    assert category is not None

    payload = {
        "category_id": str(category.id),
        "name": "Admin Test Product",
        "slug": "admin-test-product",
        "brand": "Admin Brand",
        "description": "Created through the admin API.",
        "image_url": "https://example.test/admin.png",
        "lowest_ask_cents": 19900,
        "total_sold": 0,
    }

    anonymous = client.post("/api/v1/admin/products", json=payload)
    assert anonymous.status_code == 401

    non_admin_access, _body = register_user(client, email="not-admin@example.com")
    non_admin_headers = {"Authorization": f"Bearer {non_admin_access}"}
    non_admin = client.post("/api/v1/admin/products", json=payload, headers=non_admin_headers)
    assert non_admin.status_code == 403
    assert non_admin.json()["error"]["code"] == "admin_required"

    headers = admin_headers(client, db_session)
    created = client.post("/api/v1/admin/products", json=payload, headers=headers)
    assert created.status_code == 201
    created_body = created.json()
    product_id = created_body["id"]
    assert created_body["slug"] == "admin-test-product"
    assert created_body["archived_at"] is None

    duplicate = client.post("/api/v1/admin/products", json=payload, headers=headers)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "product_slug_exists"

    missing_category_payload = {**payload, "slug": "missing-category-product", "category_id": str(uuid4())}
    missing_category = client.post("/api/v1/admin/products", json=missing_category_payload, headers=headers)
    assert missing_category.status_code == 404
    assert missing_category.json()["error"]["code"] == "category_not_found"

    managed = client.get("/api/v1/admin/products", headers=headers)
    assert managed.status_code == 200
    assert any(item["id"] == product_id for item in managed.json()["items"])

    updated = client.patch(
        f"/api/v1/admin/products/{product_id}",
        json={"name": "Admin Updated Product", "slug": "admin-updated-product"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Admin Updated Product"
    assert updated.json()["slug"] == "admin-updated-product"

    archive = client.post(f"/api/v1/admin/products/{product_id}/archive", headers=headers)
    assert archive.status_code == 200
    assert archive.json()["archived_at"] is not None
    assert archive.json()["archived_by_user_id"] is not None

    public_detail = client.get("/api/v1/products/admin-updated-product")
    assert public_detail.status_code == 404
    public_list = client.get("/api/v1/products?limit=100")
    assert "admin-updated-product" not in {item["slug"] for item in public_list.json()["items"]}
    public_search = client.get("/api/v1/search?q=admin-updated")
    assert public_search.status_code == 200
    assert public_search.json()["items"] == []

    archived_list = client.get("/api/v1/admin/products?archived=true", headers=headers)
    assert archived_list.status_code == 200
    assert any(item["id"] == product_id for item in archived_list.json()["items"])

    non_admin_archive = client.post(f"/api/v1/admin/products/{product_id}/restore", headers=non_admin_headers)
    assert non_admin_archive.status_code == 403

    restore = client.post(f"/api/v1/admin/products/{product_id}/restore", headers=headers)
    assert restore.status_code == 200
    assert restore.json()["archived_at"] is None
    assert client.get("/api/v1/products/admin-updated-product").status_code == 200


def test_marketplace_integrity_conflicts_are_stable(client: TestClient, db_session: Session, monkeypatch) -> None:
    category = db_session.scalar(select(Category).where(Category.slug == "sneakers"))
    assert category is not None
    headers = admin_headers(client, db_session, email="integrity-admin@example.com")

    monkeypatch.setattr(admin_products, "_ensure_unique_slug", lambda *_args, **_kwargs: None)
    duplicate_slug = client.post(
        "/api/v1/admin/products",
        json={
            "category_id": str(category.id),
            "name": "Duplicate Slug Race",
            "slug": "jordan-1-retro-high-test",
            "brand": "Race",
            "lowest_ask_cents": 100,
            "total_sold": 0,
        },
        headers=headers,
    )
    assert duplicate_slug.status_code == 409
    assert duplicate_slug.json()["error"]["code"] == "product_slug_exists"
    assert "UNIQUE constraint failed" not in duplicate_slug.text

    buyer_access, _body = register_user(client, email="integrity-watch@example.com")
    buyer_headers = {"Authorization": f"Bearer {buyer_access}"}
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))
    assert product is not None
    assert client.post("/api/v1/watchlist", json={"product_id": str(product.id)}, headers=buyer_headers).status_code == 201
    duplicate_watch = client.post("/api/v1/watchlist", json={"product_id": str(product.id)}, headers=buyer_headers)
    assert duplicate_watch.status_code == 409
    assert duplicate_watch.json()["error"]["code"] == "watchlist_duplicate"
    assert "UNIQUE constraint failed" not in duplicate_watch.text

    unknown_error = IntegrityError("statement", {}, Exception("foreign key constraint failed somewhere else"))
    assert matches_integrity_target(unknown_error, ("uq_products_slug", "products.slug")) is False


def test_admin_variant_management_flow(client: TestClient, db_session: Session) -> None:
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))
    assert product is not None
    headers = admin_headers(client, db_session, email="variant-admin@example.com")

    non_admin_access, _body = register_user(client, email="variant-non-admin@example.com")
    non_admin_headers = {"Authorization": f"Bearer {non_admin_access}"}
    non_admin = client.post(
        f"/api/v1/admin/products/{product.id}/variants",
        json={"size": "9", "color": "White", "sku": "DENIED"},
        headers=non_admin_headers,
    )
    assert non_admin.status_code == 403

    missing_product = client.post(
        f"/api/v1/admin/products/{uuid4()}/variants",
        json={"size": "9", "color": "White", "sku": "MISSING"},
        headers=headers,
    )
    assert missing_product.status_code == 404

    created = client.post(
        f"/api/v1/admin/products/{product.id}/variants",
        json={"size": "9", "color": "White", "sku": "J1-TEST-9"},
        headers=headers,
    )
    assert created.status_code == 201
    variant_id = created.json()["id"]

    detail = client.get("/api/v1/products/jordan-1-retro-high-test")
    assert any(variant["id"] == variant_id for variant in detail.json()["variants"])

    updated = client.patch(
        f"/api/v1/admin/product-variants/{variant_id}",
        json={"size": "9.5"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["size"] == "9.5"

    missing_variant = client.patch(
        f"/api/v1/admin/product-variants/{uuid4()}",
        json={"size": "11"},
        headers=headers,
    )
    assert missing_variant.status_code == 404

    deleted = client.delete(f"/api/v1/admin/product-variants/{variant_id}", headers=headers)
    assert deleted.status_code == 204
    detail_after_delete = client.get("/api/v1/products/jordan-1-retro-high-test")
    assert all(variant["id"] != variant_id for variant in detail_after_delete.json()["variants"])


def test_protected_listing_and_watchlist_flow(client: TestClient, db_session: Session) -> None:
    unauth_listing = client.post("/api/v1/listings", json={"product_id": str(uuid4()), "price_cents": 1000})
    assert unauth_listing.status_code == 401

    access_token, _body = register_user(client, email="seller@example.com")
    headers = {"Authorization": f"Bearer {access_token}"}
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))

    listing = client.post(
        "/api/v1/listings",
        json={"product_id": str(product.id), "price_cents": 25000, "currency": "USD"},
        headers=headers,
    )
    assert listing.status_code == 201
    assert listing.json()["status"] == "active"

    missing_product = client.post(
        "/api/v1/listings",
        json={"product_id": str(uuid4()), "price_cents": 25000, "currency": "USD"},
        headers=headers,
    )
    assert missing_product.status_code == 404

    invalid_price = client.post(
        "/api/v1/listings",
        json={"product_id": str(product.id), "price_cents": 0, "currency": "USD"},
        headers=headers,
    )
    assert invalid_price.status_code == 422

    empty_watchlist = client.get("/api/v1/watchlist", headers=headers)
    assert empty_watchlist.status_code == 200
    assert empty_watchlist.json() == []

    watched = client.post("/api/v1/watchlist", json={"product_id": str(product.id)}, headers=headers)
    assert watched.status_code == 201
    watchlist_item_id = watched.json()["id"]

    duplicate = client.post("/api/v1/watchlist", json={"product_id": str(product.id)}, headers=headers)
    assert duplicate.status_code == 409

    listed = client.get("/api/v1/watchlist", headers=headers)
    assert listed.status_code == 200
    assert listed.json()[0]["product"]["slug"] == "jordan-1-retro-high-test"

    other_access, _body = register_user(client, email="other@example.com")
    other_delete = client.delete(
        f"/api/v1/watchlist/{watchlist_item_id}",
        headers={"Authorization": f"Bearer {other_access}"},
    )
    assert other_delete.status_code == 404

    own_delete = client.delete(f"/api/v1/watchlist/{watchlist_item_id}", headers=headers)
    assert own_delete.status_code == 204
    assert db_session.get(WatchlistItem, UUID(watchlist_item_id)) is None


def test_product_detail_exposes_lowest_active_listing(client: TestClient, db_session: Session) -> None:
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))
    archived_product = db_session.scalar(select(Product).where(Product.slug == "supreme-test-hoodie"))
    assert product is not None
    assert archived_product is not None

    seller_access, _body = register_user(client, email="detail-seller@example.com")
    seller_headers = {"Authorization": f"Bearer {seller_access}"}

    higher = client.post(
        "/api/v1/listings",
        json={"product_id": str(product.id), "price_cents": 26000, "currency": "USD"},
        headers=seller_headers,
    )
    assert higher.status_code == 201
    lower = client.post(
        "/api/v1/listings",
        json={"product_id": str(product.id), "price_cents": 24000, "currency": "USD"},
        headers=seller_headers,
    )
    assert lower.status_code == 201

    detail = client.get("/api/v1/products/jordan-1-retro-high-test")
    assert detail.status_code == 200
    assert detail.json()["lowest_active_listing"]["id"] == lower.json()["id"]
    assert detail.json()["lowest_active_listing"]["price_cents"] == 24000
    assert detail.json()["lowest_active_listing"]["status"] == "active"

    lower_model = db_session.get(Listing, UUID(lower.json()["id"]))
    assert lower_model is not None
    lower_model.status = "sold"
    db_session.commit()

    detail_after_sold = client.get("/api/v1/products/jordan-1-retro-high-test")
    assert detail_after_sold.status_code == 200
    assert detail_after_sold.json()["lowest_active_listing"]["id"] == higher.json()["id"]

    higher_model = db_session.get(Listing, UUID(higher.json()["id"]))
    assert higher_model is not None
    higher_model.status = "cancelled"
    db_session.commit()

    detail_without_active = client.get("/api/v1/products/jordan-1-retro-high-test")
    assert detail_without_active.status_code == 200
    assert detail_without_active.json()["lowest_active_listing"] is None

    archived_listing = client.post(
        "/api/v1/listings",
        json={"product_id": str(archived_product.id), "price_cents": 9000, "currency": "USD"},
        headers=seller_headers,
    )
    assert archived_listing.status_code == 201
    archived_product.archived_at = datetime.now(UTC)
    db_session.commit()

    assert client.get("/api/v1/products/supreme-test-hoodie").status_code == 404


def test_listing_management_and_archived_product_rejection(client: TestClient, db_session: Session) -> None:
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))
    archived_product = db_session.scalar(select(Product).where(Product.slug == "supreme-test-hoodie"))
    assert product is not None
    assert archived_product is not None

    assert client.get("/api/v1/listings").status_code == 401

    seller_access, _body = register_user(client, email="listing-seller@example.com")
    seller_headers = {"Authorization": f"Bearer {seller_access}"}
    other_access, _body = register_user(client, email="listing-other@example.com")
    other_headers = {"Authorization": f"Bearer {other_access}"}

    created = client.post(
        "/api/v1/listings",
        json={"product_id": str(product.id), "price_cents": 25100, "currency": "USD"},
        headers=seller_headers,
    )
    assert created.status_code == 201
    listing_id = created.json()["id"]

    seller_list = client.get("/api/v1/listings", headers=seller_headers)
    assert seller_list.status_code == 200
    seller_body = seller_list.json()
    assert seller_body["total"] == 1
    assert seller_body["items"][0]["id"] == listing_id
    assert seller_body["items"][0]["user_id"] == created.json()["user_id"]
    assert seller_body["items"][0]["product"]["slug"] == "jordan-1-retro-high-test"
    assert {"id", "user_id", "product", "price_cents", "currency", "status", "created_at", "updated_at"}.issubset(
        seller_body["items"][0].keys()
    )

    other_list = client.get("/api/v1/listings", headers=other_headers)
    assert other_list.status_code == 200
    assert other_list.json()["items"] == []

    cross_cancel = client.post(f"/api/v1/listings/{listing_id}/cancel", headers=other_headers)
    assert cross_cancel.status_code == 404

    own_cancel = client.post(f"/api/v1/listings/{listing_id}/cancel", headers=seller_headers)
    assert own_cancel.status_code == 200
    assert own_cancel.json()["status"] == "cancelled"

    idempotent_cancel = client.post(f"/api/v1/listings/{listing_id}/cancel", headers=seller_headers)
    assert idempotent_cancel.status_code == 200
    assert idempotent_cancel.json()["status"] == "cancelled"

    missing_cancel = client.post(f"/api/v1/listings/{uuid4()}/cancel", headers=seller_headers)
    assert missing_cancel.status_code == 404

    active_for_admin = client.post(
        "/api/v1/listings",
        json={"product_id": str(product.id), "price_cents": 25200, "currency": "USD"},
        headers=other_headers,
    )
    assert active_for_admin.status_code == 201
    active_listing_id = active_for_admin.json()["id"]

    admin_headers_value = admin_headers(client, db_session, email="listing-admin@example.com")
    assert client.get("/api/v1/admin/listings").status_code == 401
    non_admin = client.get("/api/v1/admin/listings", headers=seller_headers)
    assert non_admin.status_code == 403

    admin_active_list = client.get("/api/v1/admin/listings?status=active", headers=admin_headers_value)
    assert admin_active_list.status_code == 200
    assert any(item["id"] == active_listing_id for item in admin_active_list.json()["items"])
    assert all(item["status"] == "active" for item in admin_active_list.json()["items"])

    admin_cancel = client.post(f"/api/v1/admin/listings/{active_listing_id}/cancel", headers=admin_headers_value)
    assert admin_cancel.status_code == 200
    assert admin_cancel.json()["status"] == "cancelled"

    non_admin_cancel = client.post(f"/api/v1/admin/listings/{listing_id}/cancel", headers=seller_headers)
    assert non_admin_cancel.status_code == 403

    archived_product.archived_at = datetime.now(UTC)
    db_session.commit()
    archived_create = client.post(
        "/api/v1/listings",
        json={"product_id": str(archived_product.id), "price_cents": 10000, "currency": "USD"},
        headers=seller_headers,
    )
    assert archived_create.status_code == 409
    assert archived_create.json()["error"]["code"] == "product_archived"


def test_authenticated_cart_flow_and_user_scoping(client: TestClient, db_session: Session) -> None:
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))
    assert product is not None

    seller_access, _body = register_user(client, email="cart-seller@example.com")
    seller_headers = {"Authorization": f"Bearer {seller_access}"}
    listing = client.post(
        "/api/v1/listings",
        json={"product_id": str(product.id), "price_cents": 24400, "currency": "USD"},
        headers=seller_headers,
    )
    assert listing.status_code == 201
    listing_id = listing.json()["id"]

    assert client.get("/api/v1/cart").status_code == 401
    assert client.post("/api/v1/cart/items", json={"listing_id": listing_id}).status_code == 401

    buyer_access, _body = register_user(client, email="cart-buyer@example.com")
    buyer_headers = {"Authorization": f"Bearer {buyer_access}"}
    empty = client.get("/api/v1/cart", headers=buyer_headers)
    assert empty.status_code == 200
    assert empty.json() == {"items": [], "total_quantity": 0}

    added = client.post(
        "/api/v1/cart/items",
        json={"listing_id": listing_id, "quantity": 2},
        headers=buyer_headers,
    )
    assert added.status_code == 201
    item_id = added.json()["id"]
    assert added.json()["quantity"] == 2
    assert added.json()["available"] is True
    assert added.json()["listing"]["product"]["slug"] == "jordan-1-retro-high-test"

    merged = client.post(
        "/api/v1/cart/items",
        json={"listing_id": listing_id, "quantity": 3},
        headers=buyer_headers,
    )
    assert merged.status_code == 201
    assert merged.json()["id"] == item_id
    assert merged.json()["quantity"] == 5
    assert "UNIQUE constraint failed" not in merged.text

    updated = client.patch(f"/api/v1/cart/items/{item_id}", json={"quantity": 4}, headers=buyer_headers)
    assert updated.status_code == 200
    assert updated.json()["quantity"] == 4

    other_access, _body = register_user(client, email="cart-other@example.com")
    other_headers = {"Authorization": f"Bearer {other_access}"}
    assert client.patch(f"/api/v1/cart/items/{item_id}", json={"quantity": 1}, headers=other_headers).status_code == 404
    assert client.delete(f"/api/v1/cart/items/{item_id}", headers=other_headers).status_code == 404

    cart = client.get("/api/v1/cart", headers=buyer_headers)
    assert cart.status_code == 200
    assert cart.json()["total_quantity"] == 4
    assert cart.json()["items"][0]["id"] == item_id

    assert client.post("/api/v1/cart/items", json={"listing_id": str(uuid4())}, headers=buyer_headers).status_code == 404

    inactive_listing = client.post(
        "/api/v1/listings",
        json={"product_id": str(product.id), "price_cents": 24500, "currency": "USD"},
        headers=seller_headers,
    )
    inactive_listing_id = inactive_listing.json()["id"]
    inactive_model = db_session.get(Listing, UUID(inactive_listing_id))
    assert inactive_model is not None
    inactive_model.status = "sold"
    db_session.commit()

    inactive_add = client.post("/api/v1/cart/items", json={"listing_id": inactive_listing_id}, headers=buyer_headers)
    assert inactive_add.status_code == 409
    assert inactive_add.json()["error"]["code"] == "listing_unavailable"

    existing_listing = db_session.get(Listing, UUID(listing_id))
    assert existing_listing is not None
    existing_listing.status = "sold"
    db_session.commit()
    unavailable_cart = client.get("/api/v1/cart", headers=buyer_headers)
    assert unavailable_cart.status_code == 200
    assert unavailable_cart.json()["items"][0]["available"] is False
    assert unavailable_cart.json()["items"][0]["unavailable_reason"] == "listing_sold"

    existing_listing.status = "active"
    product.archived_at = datetime.now(UTC)
    db_session.commit()
    archived_cart = client.get("/api/v1/cart", headers=buyer_headers)
    assert archived_cart.status_code == 200
    assert archived_cart.json()["items"][0]["available"] is False
    assert archived_cart.json()["items"][0]["unavailable_reason"] == "product_archived"

    archived_add = client.post("/api/v1/cart/items", json={"listing_id": inactive_listing_id}, headers=buyer_headers)
    assert archived_add.status_code == 409
    assert archived_add.json()["error"]["code"] == "product_archived"

    removed = client.delete(f"/api/v1/cart/items/{item_id}", headers=buyer_headers)
    assert removed.status_code == 204
    assert client.get("/api/v1/cart", headers=buyer_headers).json() == {"items": [], "total_quantity": 0}
