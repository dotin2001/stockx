from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password, verify_password
from app.models import Product, RefreshToken, User, WatchlistItem
from app.schemas.product import ProductSummary
from app.services import auth as auth_service


def register_user(client: TestClient, email: str = "buyer@example.com") -> tuple[str, dict]:
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Buyer", "email": email, "password": "password123"},
    )
    assert response.status_code == 201
    body = response.json()
    return body["access_token"], body


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

    search = client.get("/api/v1/search?q=jordan")
    assert search.status_code == 200
    assert search.json()["items"][0]["slug"] == "jordan-1-retro-high-test"


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
