from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.core.config import Settings
from app.core.security import hash_password, verify_password
from app.models import Category, CustomerAdminMessage, Listing, Product, ProductVariant, RefreshToken, SellerProfile, User, WatchlistItem
from app.schemas.admin_user import AdminUserRead
from app.schemas.product import ProductCreate, ProductDiscoveryQuery, ProductDiscoverySort, ProductSummary
from app.services import admin_users
from app.services import admin_products
from app.services import auth as auth_service
from app.services import listings as listing_service
from app.services.admin_bootstrap import AdminPromotionError, grant_supreme_admin, promote_existing_user
from app.services.integrity import matches_integrity_target


def register_user(client: TestClient, email: str = "buyer@example.com") -> tuple[str, dict]:
    response = client.post(
        "/api/v1/auth/register",
        json={"name": "Buyer", "email": email, "password": "password123"},
    )
    assert response.status_code == 201
    body = response.json()
    return body["access_token"], body


def seller_profile_payload(**overrides) -> dict:
    payload = {
        "phone_number": "+15555550123",
        "address_line1": "123 Market Street",
        "address_line2": "Suite 4",
        "city": "San Francisco",
        "state": "CA",
        "postal_code": "94105",
        "country": "US",
    }
    payload.update(overrides)
    return payload


def admin_headers(client: TestClient, db_session: Session, email: str = "admin@example.com") -> dict[str, str]:
    access_token, _body = register_user(client, email=email)
    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    user.is_admin = True
    db_session.commit()
    return {"Authorization": f"Bearer {access_token}"}


def supreme_admin_headers(client: TestClient, db_session: Session, email: str = "supreme@example.com") -> dict[str, str]:
    access_token, _body = register_user(client, email=email)
    user = db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    user.is_admin = True
    user.is_supreme_admin = True
    db_session.commit()
    return {"Authorization": f"Bearer {access_token}"}


def create_store_listing(
    db_session: Session,
    product: Product,
    *,
    product_variant: ProductVariant | None = None,
    price_cents: int = 25000,
    status: str = "active",
    available_quantity: int = 10,
    email: str | None = None,
) -> Listing:
    user = User(
        name="Store Admin",
        email=email or f"store-admin-{uuid4()}@example.com",
        password_hash=hash_password("password123"),
        is_admin=True,
    )
    listing = Listing(
        user=user,
        product=product,
        product_variant=product_variant,
        price_cents=price_cents,
        available_quantity=available_quantity,
        currency="USD",
        status=status,
    )
    db_session.add_all([user, listing])
    db_session.commit()
    db_session.refresh(listing)
    return listing


def create_catalog_product(
    db_session: Session,
    category: Category,
    *,
    name: str,
    slug: str,
    brand: str,
    size: str | None = None,
    total_sold: int = 0,
) -> Product:
    product = Product(
        category=category,
        name=name,
        slug=slug,
        brand=brand,
        description=f"{name} test product.",
        image_url=f"https://example.test/{slug}.png",
        lowest_ask_cents=None,
        total_sold=total_sold,
    )
    db_session.add(product)
    if size is not None:
        db_session.add(ProductVariant(product=product, size=size, color="Test", sku=f"{slug}-{size}"))
    db_session.commit()
    db_session.refresh(product)
    return product


def assert_public_user_roles(payload: dict, *, is_admin: bool, is_supreme_admin: bool) -> None:
    assert payload["is_admin"] is is_admin
    assert payload["is_supreme_admin"] is is_supreme_admin


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


def test_user_model_supports_customer_admin_and_supreme_admin(db_session: Session) -> None:
    customer = User(name="Customer", email="customer-role@example.com", password_hash=hash_password("password123"))
    normal_admin = User(
        name="Normal Admin",
        email="normal-admin-role@example.com",
        password_hash=hash_password("password123"),
        is_admin=True,
    )
    supreme_admin = User(
        name="Supreme Admin",
        email="supreme-admin-role@example.com",
        password_hash=hash_password("password123"),
        is_admin=True,
        is_supreme_admin=True,
    )

    db_session.add_all([customer, normal_admin, supreme_admin])
    db_session.commit()

    saved_customer = db_session.scalar(select(User).where(User.email == "customer-role@example.com"))
    saved_normal_admin = db_session.scalar(select(User).where(User.email == "normal-admin-role@example.com"))
    saved_supreme_admin = db_session.scalar(select(User).where(User.email == "supreme-admin-role@example.com"))
    assert saved_customer is not None
    assert saved_normal_admin is not None
    assert saved_supreme_admin is not None
    assert saved_customer.is_admin is False
    assert saved_customer.is_supreme_admin is False
    assert saved_normal_admin.is_admin is True
    assert saved_normal_admin.is_supreme_admin is False
    assert saved_supreme_admin.is_admin is True
    assert saved_supreme_admin.is_supreme_admin is True


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


def test_supreme_admin_grant_service_preserves_auth_data(db_session: Session) -> None:
    user = auth_service.register_user(
        db_session,
        name="Supreme Me",
        email="supreme-promote@example.com",
        password="password123",
    )
    _record, _raw_token = auth_service.create_refresh_token_record(db_session, user)
    password_hash = user.password_hash
    refresh_token_ids = {token.id for token in user.refresh_tokens}

    promoted = grant_supreme_admin(db_session, email="  SUPREME-PROMOTE@example.com ")
    db_session.commit()

    assert promoted.id == user.id
    assert promoted.email == "supreme-promote@example.com"
    assert promoted.is_admin is True
    assert promoted.is_supreme_admin is True
    assert promoted.password_hash == password_hash
    assert {token.id for token in promoted.refresh_tokens} == refresh_token_ids

    promoted_again = grant_supreme_admin(db_session, email="supreme-promote@example.com")
    db_session.commit()
    assert promoted_again.id == user.id
    assert promoted_again.is_admin is True
    assert promoted_again.is_supreme_admin is True
    assert promoted_again.password_hash == password_hash

    with pytest.raises(AdminPromotionError):
        grant_supreme_admin(db_session, email="missing-supreme@example.com")


def test_admin_user_schema_serialization_excludes_password(db_session: Session) -> None:
    user = User(
        name="Schema Admin",
        email="schema-admin@example.com",
        password_hash=hash_password("password123"),
        is_admin=True,
        is_supreme_admin=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    serialized = AdminUserRead.model_validate(user).model_dump()

    assert {
        "id",
        "name",
        "email",
        "is_admin",
        "is_supreme_admin",
        "created_at",
        "updated_at",
    }.issubset(serialized.keys())
    assert "password_hash" not in serialized


def test_admin_user_management_service_rules(db_session: Session) -> None:
    supreme = User(
        name="Supreme",
        email="supreme-service@example.com",
        password_hash=hash_password("password123"),
        is_admin=True,
        is_supreme_admin=True,
    )
    customer = User(name="Customer", email="customer-service@example.com", password_hash=hash_password("password123"))
    normal_admin = User(
        name="Normal",
        email="normal-service@example.com",
        password_hash=hash_password("password123"),
        is_admin=True,
    )
    other_supreme = User(
        name="Other Supreme",
        email="other-supreme-service@example.com",
        password_hash=hash_password("password123"),
        is_admin=True,
        is_supreme_admin=True,
    )
    db_session.add_all([supreme, customer, normal_admin, other_supreme])
    db_session.commit()

    promoted = admin_users.promote_user_by_email(db_session, email=" CUSTOMER-SERVICE@example.com ")
    db_session.commit()
    assert promoted.id == customer.id
    assert promoted.is_admin is True
    assert promoted.is_supreme_admin is False

    promoted_again = admin_users.promote_user_by_id(db_session, user_id=normal_admin.id)
    db_session.commit()
    assert promoted_again.id == normal_admin.id
    assert promoted_again.is_admin is True
    assert promoted_again.is_supreme_admin is False

    with pytest.raises(APIError) as missing:
        admin_users.promote_user_by_email(db_session, email="missing-service@example.com")
    assert missing.value.status_code == 404

    with pytest.raises(APIError) as self_demote:
        admin_users.demote_user(db_session, user_id=supreme.id, actor=supreme)
    assert self_demote.value.code == "self_demotion_rejected"

    with pytest.raises(APIError) as supreme_demote:
        admin_users.demote_user(db_session, user_id=other_supreme.id, actor=supreme)
    assert supreme_demote.value.code == "supreme_admin_protected"

    demoted = admin_users.demote_user(db_session, user_id=normal_admin.id, actor=supreme)
    db_session.commit()
    assert demoted.is_admin is False
    assert demoted.is_supreme_admin is False


def test_schema_serialization_for_product_summary(db_session: Session) -> None:
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))

    summary = ProductSummary.model_validate(product)
    dumped = summary.model_dump()

    assert summary.slug == "jordan-1-retro-high-test"
    assert summary.category.slug == "sneakers"
    assert summary.lowest_ask_cents == 24300
    assert "available_quantity" not in dumped
    assert "inventory_summary" not in dumped


def test_auth_register_login_me_refresh_and_logout(client: TestClient, db_session: Session) -> None:
    access_token, body = register_user(client)

    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "buyer@example.com"
    assert body["user"]["is_seller"] is False
    assert_public_user_roles(body["user"], is_admin=False, is_supreme_admin=False)
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
    assert_public_user_roles(login.json()["user"], is_admin=False, is_supreme_admin=False)
    assert "stockx_refresh" in client.cookies

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "buyer@example.com"
    assert me.json()["is_seller"] is False
    assert_public_user_roles(me.json(), is_admin=False, is_supreme_admin=False)

    old_refresh = client.cookies.get("stockx_refresh")
    refresh = client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 200
    assert refresh.json()["access_token"] != access_token
    assert_public_user_roles(refresh.json()["user"], is_admin=False, is_supreme_admin=False)
    assert client.cookies.get("stockx_refresh") != old_refresh

    replay = client.post("/api/v1/auth/refresh", cookies={"stockx_refresh": old_refresh})
    assert replay.status_code == 401

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204
    assert "stockx_refresh" not in client.cookies

    revoked_count = len(db_session.scalars(select(RefreshToken).where(RefreshToken.revoked_at.is_not(None))).all())
    assert revoked_count >= 2


def test_seller_profile_flow_is_disabled_for_customers(client: TestClient, db_session: Session) -> None:
    assert client.get("/api/v1/seller/profile").status_code == 401
    assert client.put("/api/v1/seller/profile", json=seller_profile_payload()).status_code == 401

    access_token, _body = register_user(client, email="profile-customer@example.com")
    headers = {"Authorization": f"Bearer {access_token}"}

    missing = client.put("/api/v1/seller/profile", json={"phone_number": "+15555550123"}, headers=headers)
    assert missing.status_code == 422

    before = client.get("/api/v1/seller/profile", headers=headers)
    assert before.status_code == 404
    assert before.json()["error"]["code"] == "seller_profile_not_found"

    disabled = client.put("/api/v1/seller/profile", json=seller_profile_payload(), headers=headers)
    assert disabled.status_code == 410
    assert disabled.json()["error"]["code"] == "seller_flow_disabled"

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["is_seller"] is False

    user = db_session.scalar(select(User).where(User.email == "profile-customer@example.com"))
    assert user is not None
    profiles = db_session.scalars(select(SellerProfile).where(SellerProfile.user_id == user.id)).all()
    assert profiles == []


def test_catalog_product_category_detail_and_search(client: TestClient) -> None:
    products = client.get("/api/v1/products?limit=1&offset=0")
    assert products.status_code == 200
    assert products.json()["limit"] == 1
    assert products.json()["total"] == 2
    assert products.json()["discovery"]["total"] == 2
    assert products.json()["discovery"]["limit"] == 1
    assert products.json()["discovery"]["offset"] == 0
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


def test_product_discovery_query_schema_validation() -> None:
    query = ProductDiscoveryQuery(
        q=" dunk ",
        brands=[" Nike ", "nike", "", "Jordan"],
        sizes="10",
        min_price_cents=1000,
        max_price_cents=2000,
        available_only=True,
        sort=ProductDiscoverySort.PRICE_ASC,
    )

    assert query.q == "dunk"
    assert query.brands == ["Nike", "Jordan"]
    assert query.sizes == ["10"]
    assert query.available_only is True
    assert query.sort == ProductDiscoverySort.PRICE_ASC

    with pytest.raises(ValidationError):
        ProductDiscoveryQuery(sort="not-a-sort")
    with pytest.raises(ValidationError):
        ProductDiscoveryQuery(min_price_cents=-1)
    with pytest.raises(ValidationError):
        ProductDiscoveryQuery(min_price_cents=3000, max_price_cents=2000)


def test_product_storefront_content_schema_validation() -> None:
    product = ProductCreate(
        category_id=uuid4(),
        name="Store Product",
        slug="store-product",
        feature_bullets=[" Premium cotton ", ""],
        detail_rows=[{"label": "Material", "value": "Cotton fleece"}],
        gallery_images=[{"url": "https://example.test/product.png", "alt": " Front "}],
    )

    assert product.feature_bullets == ["Premium cotton"]
    assert product.detail_rows[0].label == "Material"
    assert product.gallery_images[0].alt == "Front"

    with pytest.raises(ValidationError):
        ProductCreate(
            category_id=uuid4(),
            name="Bad Image",
            slug="bad-image",
            gallery_images=[{"url": "ftp://example.test/product.png"}],
        )


def test_public_product_discovery_filters_sorting_and_metadata(client: TestClient, db_session: Session) -> None:
    sneakers = db_session.scalar(select(Category).where(Category.slug == "sneakers"))
    streetwear = db_session.scalar(select(Category).where(Category.slug == "streetwear"))
    assert sneakers is not None
    assert streetwear is not None

    jordan = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))
    hoodie = db_session.scalar(select(Product).where(Product.slug == "supreme-test-hoodie"))
    assert jordan is not None
    assert hoodie is not None
    db_session.add(ProductVariant(product=hoodie, size="M", color="Black", sku="HOODIE-M"))
    runner = create_catalog_product(
        db_session,
        sneakers,
        name="Nike Test Runner",
        slug="nike-test-runner",
        brand="Nike",
        size="9",
        total_sold=30,
    )
    adidas = create_catalog_product(
        db_session,
        sneakers,
        name="Adidas Test Forum",
        slug="adidas-test-forum",
        brand="Adidas",
        size="10",
        total_sold=1,
    )

    create_store_listing(db_session, jordan, price_cents=24000)
    create_store_listing(db_session, runner, price_cents=18000)
    create_store_listing(db_session, hoodie, price_cents=6000)
    create_store_listing(db_session, adidas, price_cents=17000, status="sold", available_quantity=0)

    category_brand = client.get("/api/v1/categories/sneakers/products?brand=Jordan")
    assert category_brand.status_code == 200
    assert [item["slug"] for item in category_brand.json()["items"]] == ["jordan-1-retro-high-test"]
    assert category_brand.json()["discovery"]["selected"]["brands"] == ["Jordan"]
    assert category_brand.json()["discovery"]["total"] == 1

    search_brand = client.get("/api/v1/search?q=test&brand=Nike")
    assert search_brand.status_code == 200
    assert [item["slug"] for item in search_brand.json()["items"]] == ["nike-test-runner"]

    size_filter = client.get("/api/v1/categories/sneakers/products?size=10&sort=name_asc")
    assert size_filter.status_code == 200
    assert [item["slug"] for item in size_filter.json()["items"]] == [
        "adidas-test-forum",
        "jordan-1-retro-high-test",
    ]

    available_size = client.get("/api/v1/categories/sneakers/products?size=10&available_only=true")
    assert available_size.status_code == 200
    assert [item["slug"] for item in available_size.json()["items"]] == ["jordan-1-retro-high-test"]

    price_range = client.get("/api/v1/products?min_price=10000&max_price=20000")
    assert price_range.status_code == 200
    assert [item["slug"] for item in price_range.json()["items"]] == ["nike-test-runner"]

    price_sorted = client.get("/api/v1/products?sort=price_asc&limit=10")
    assert price_sorted.status_code == 200
    assert [item["slug"] for item in price_sorted.json()["items"]][:3] == [
        "supreme-test-hoodie",
        "nike-test-runner",
        "jordan-1-retro-high-test",
    ]
    assert price_sorted.json()["items"][-1]["slug"] == "adidas-test-forum"

    popularity_sorted = client.get("/api/v1/categories/sneakers/products?sort=popular")
    assert popularity_sorted.status_code == 200
    assert popularity_sorted.json()["items"][0]["slug"] == "nike-test-runner"

    no_matches = client.get("/api/v1/products?brand=Nope")
    assert no_matches.status_code == 200
    assert no_matches.json()["items"] == []
    assert no_matches.json()["total"] == 0
    assert no_matches.json()["discovery"]["selected"]["brands"] == ["Nope"]
    assert {option["value"] for option in no_matches.json()["discovery"]["brands"]} >= {"Jordan", "Nike", "Supreme"}
    assert no_matches.json()["discovery"]["price_bounds"] == {"min_cents": None, "max_cents": None}

    metadata = price_sorted.json()["discovery"]
    assert {option["value"] for option in metadata["brands"]} >= {"Jordan", "Nike", "Supreme"}
    assert {option["value"] for option in metadata["sizes"]} >= {"9", "10", "M"}
    assert metadata["price_bounds"] == {"min_cents": 6000, "max_cents": 24000}
    assert metadata["sort"] == "price_asc"


def test_public_product_discovery_validation_and_archived_exclusion(client: TestClient, db_session: Session) -> None:
    hoodie = db_session.scalar(select(Product).where(Product.slug == "supreme-test-hoodie"))
    assert hoodie is not None
    create_store_listing(db_session, hoodie, price_cents=6000)

    bad_sort = client.get("/api/v1/products?sort=not-a-sort")
    assert bad_sort.status_code == 422
    assert bad_sort.json()["error"]["code"] == "validation_error"

    bad_price = client.get("/api/v1/products?min_price=-1")
    assert bad_price.status_code == 422
    assert bad_price.json()["error"]["code"] == "validation_error"

    bad_range = client.get("/api/v1/products?min_price=2000&max_price=1000")
    assert bad_range.status_code == 422
    assert bad_range.json()["error"]["code"] == "validation_error"

    hoodie.archived_at = datetime.now(UTC)
    db_session.commit()

    archived_search = client.get("/api/v1/search?q=hoodie")
    assert archived_search.status_code == 200
    assert archived_search.json()["items"] == []
    assert archived_search.json()["discovery"]["brands"] == []


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
        "feature_bullets": ["Limited store release", "Premium construction"],
        "detail_rows": [{"label": "Material", "value": "Leather"}],
        "gallery_images": [{"url": "https://example.test/admin-detail.png", "alt": "Detail view"}],
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
    assert created_body["feature_bullets"] == ["Limited store release", "Premium construction"]
    assert created_body["detail_rows"] == [{"label": "Material", "value": "Leather"}]
    assert created_body["gallery_images"][0]["url"] == "https://example.test/admin-detail.png"

    duplicate = client.post("/api/v1/admin/products", json=payload, headers=headers)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "product_slug_exists"

    missing_category_payload = {**payload, "slug": "missing-category-product", "category_id": str(uuid4())}
    missing_category = client.post("/api/v1/admin/products", json=missing_category_payload, headers=headers)
    assert missing_category.status_code == 404
    assert missing_category.json()["error"]["code"] == "category_not_found"

    managed = client.get("/api/v1/admin/products", headers=headers)
    assert managed.status_code == 200
    managed_product = next(item for item in managed.json()["items"] if item["id"] == product_id)
    assert managed_product["inventory_summary"] == {
        "total_listings": 0,
        "active_listings": 0,
        "total_available_quantity": 0,
        "lowest_active_price_cents": None,
    }
    assert managed_product["inventory_items"] == []

    updated = client.patch(
        f"/api/v1/admin/products/{product_id}",
        json={
            "name": "Admin Updated Product",
            "slug": "admin-updated-product",
            "feature_bullets": [],
            "detail_rows": [{"label": "Care", "value": "Spot clean"}],
            "gallery_images": [],
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Admin Updated Product"
    assert updated.json()["slug"] == "admin-updated-product"
    assert updated.json()["feature_bullets"] == []
    assert updated.json()["detail_rows"] == [{"label": "Care", "value": "Spot clean"}]
    assert updated.json()["gallery_images"] == []

    invalid_content = client.patch(
        f"/api/v1/admin/products/{product_id}",
        json={"gallery_images": [{"url": "ftp://example.test/bad.png"}]},
        headers=headers,
    )
    assert invalid_content.status_code == 422

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


def test_supreme_admin_user_management_api(client: TestClient, db_session: Session) -> None:
    customer_access, _body = register_user(client, email="managed-customer@example.com")
    customer_headers = {"Authorization": f"Bearer {customer_access}"}
    normal_headers = admin_headers(client, db_session, email="managed-normal@example.com")
    supreme_headers = supreme_admin_headers(client, db_session, email="managed-supreme@example.com")

    customer = db_session.scalar(select(User).where(User.email == "managed-customer@example.com"))
    normal = db_session.scalar(select(User).where(User.email == "managed-normal@example.com"))
    supreme = db_session.scalar(select(User).where(User.email == "managed-supreme@example.com"))
    assert customer is not None
    assert normal is not None
    assert supreme is not None

    anonymous = client.get("/api/v1/admin/users")
    assert anonymous.status_code == 401

    rejected_customer = client.post("/api/v1/admin/users/promote", json={"email": customer.email}, headers=customer_headers)
    assert rejected_customer.status_code == 403
    rejected_normal = client.post("/api/v1/admin/users/promote", json={"email": customer.email}, headers=normal_headers)
    assert rejected_normal.status_code == 403
    db_session.refresh(customer)
    assert customer.is_admin is False

    listed = client.get("/api/v1/admin/users?search=managed-&limit=10&offset=0", headers=supreme_headers)
    assert listed.status_code == 200
    list_body = listed.json()
    assert list_body["total"] >= 3
    assert {"id", "name", "email", "is_admin", "is_supreme_admin", "created_at", "updated_at"}.issubset(
        list_body["items"][0].keys()
    )
    assert "password_hash" not in list_body["items"][0]

    promoted_by_email = client.post(
        "/api/v1/admin/users/promote",
        json={"email": " MANAGED-CUSTOMER@example.com "},
        headers=supreme_headers,
    )
    assert promoted_by_email.status_code == 200
    assert promoted_by_email.json()["email"] == customer.email
    assert_public_user_roles(promoted_by_email.json(), is_admin=True, is_supreme_admin=False)

    promoted_by_id = client.post(f"/api/v1/admin/users/{normal.id}/promote", headers=supreme_headers)
    assert promoted_by_id.status_code == 200
    assert_public_user_roles(promoted_by_id.json(), is_admin=True, is_supreme_admin=False)

    missing = client.post(f"/api/v1/admin/users/{uuid4()}/promote", headers=supreme_headers)
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "user_not_found"

    demote_self = client.post(f"/api/v1/admin/users/{supreme.id}/demote", headers=supreme_headers)
    assert demote_self.status_code == 409
    assert demote_self.json()["error"]["code"] == "self_demotion_rejected"

    demoted = client.post(f"/api/v1/admin/users/{normal.id}/demote", headers=supreme_headers)
    assert demoted.status_code == 200
    assert_public_user_roles(demoted.json(), is_admin=False, is_supreme_admin=False)

    db_session.refresh(supreme)
    assert supreme.is_admin is True
    assert supreme.is_supreme_admin is True


def test_supreme_admin_role_flow(client: TestClient, db_session: Session) -> None:
    customer_access, _body = register_user(client, email="role-flow-customer@example.com")
    supreme_headers = supreme_admin_headers(client, db_session, email="role-flow-supreme@example.com")
    customer = db_session.scalar(select(User).where(User.email == "role-flow-customer@example.com"))
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))
    assert customer is not None
    assert product is not None

    assert client.get("/api/v1/admin/products", headers={"Authorization": f"Bearer {customer_access}"}).status_code == 403

    promoted = client.post(f"/api/v1/admin/users/{customer.id}/promote", headers=supreme_headers)
    assert promoted.status_code == 200

    normal_admin_headers = {"Authorization": f"Bearer {customer_access}"}
    normal_admin_products = client.get("/api/v1/admin/products", headers=normal_admin_headers)
    assert normal_admin_products.status_code == 200

    normal_admin_users = client.get("/api/v1/admin/users", headers=normal_admin_headers)
    assert normal_admin_users.status_code == 403

    listing = create_store_listing(db_session, product, price_cents=24400, available_quantity=2)
    listing_id = str(listing.id)
    normal_quantity_mutation = client.post(
        f"/api/v1/admin/listings/{listing_id}/inventory/quantity",
        json={"adjustment": -1},
        headers=normal_admin_headers,
    )
    assert normal_quantity_mutation.status_code == 403
    db_session.refresh(listing)
    assert listing.available_quantity == 2

    buyer_access, _buyer_body = register_user(client, email="role-flow-buyer@example.com")
    buyer_headers = {"Authorization": f"Bearer {buyer_access}"}
    carted = client.post("/api/v1/cart/items", json={"listing_id": listing_id, "quantity": 2}, headers=buyer_headers)
    assert carted.status_code == 201
    detail_before_inventory_change = client.get("/api/v1/products/jordan-1-retro-high-test")
    assert detail_before_inventory_change.status_code == 200
    assert detail_before_inventory_change.json()["lowest_active_listing"]["id"] == listing_id

    zeroed = client.post(
        f"/api/v1/admin/listings/{listing_id}/inventory/quantity",
        json={"adjustment": -2},
        headers=supreme_headers,
    )
    assert zeroed.status_code == 200
    assert zeroed.json()["available_quantity"] == 0
    detail_after_quantity_change = client.get("/api/v1/products/jordan-1-retro-high-test")
    assert detail_after_quantity_change.status_code == 200
    assert detail_after_quantity_change.json()["lowest_active_listing"] is None
    cart_after_quantity_change = client.get("/api/v1/cart", headers=buyer_headers)
    assert cart_after_quantity_change.status_code == 200
    assert cart_after_quantity_change.json()["items"][0]["available"] is False
    assert cart_after_quantity_change.json()["items"][0]["unavailable_reason"] == "inventory_unavailable"

    sold = client.patch(
        f"/api/v1/admin/listings/{listing_id}/inventory/status",
        json={"status": "sold"},
        headers=supreme_headers,
    )
    assert sold.status_code == 200
    assert sold.json()["status"] == "sold"

    demoted = client.post(f"/api/v1/admin/users/{customer.id}/demote", headers=supreme_headers)
    assert demoted.status_code == 200

    removed_admin_products = client.get("/api/v1/admin/products", headers=normal_admin_headers)
    assert removed_admin_products.status_code == 403


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

    access_token, _body = register_user(client, email="customer-listing@example.com")
    headers = {"Authorization": f"Bearer {access_token}"}
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))

    customer_listing = client.post(
        "/api/v1/listings",
        json={"product_id": str(product.id), "price_cents": 25000, "currency": "USD"},
        headers=headers,
    )
    assert customer_listing.status_code == 403
    assert customer_listing.json()["error"]["code"] == "admin_required"

    admin_headers_value = admin_headers(client, db_session, email="store-listing-admin@example.com")
    listing = client.post(
        "/api/v1/listings",
        json={"product_id": str(product.id), "price_cents": 25000, "currency": "USD"},
        headers=admin_headers_value,
    )
    assert listing.status_code == 201
    assert listing.json()["status"] == "active"

    missing_product = client.post(
        "/api/v1/listings",
        json={"product_id": str(uuid4()), "price_cents": 25000, "currency": "USD"},
        headers=admin_headers_value,
    )
    assert missing_product.status_code == 404

    invalid_price = client.post(
        "/api/v1/listings",
        json={"product_id": str(product.id), "price_cents": 0, "currency": "USD"},
        headers=admin_headers_value,
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


def test_customer_admin_message_flow(client: TestClient, db_session: Session) -> None:
    assert client.get("/api/v1/messages").status_code == 401
    assert client.post("/api/v1/messages", json={"subject": "Hi", "body": "Help"}).status_code == 401
    assert client.get("/api/v1/admin/messages").status_code == 401

    customer_access, _body = register_user(client, email="message-customer@example.com")
    customer_headers = {"Authorization": f"Bearer {customer_access}"}
    other_access, _body = register_user(client, email="message-other@example.com")
    other_headers = {"Authorization": f"Bearer {other_access}"}
    admin_headers_value = admin_headers(client, db_session, email="message-admin@example.com")

    invalid = client.post("/api/v1/messages", json={"subject": "   ", "body": "   "}, headers=customer_headers)
    assert invalid.status_code == 422

    created = client.post(
        "/api/v1/messages",
        json={"subject": "Order question", "body": "Can you help me choose a size?"},
        headers=customer_headers,
    )
    assert created.status_code == 201
    created_body = created.json()
    message_id = created_body["id"]
    assert created_body["sender_email"] == "message-customer@example.com"
    assert created_body["subject"] == "Order question"
    assert created_body["is_read"] is False
    assert created_body["read_at"] is None

    message_record = db_session.get(CustomerAdminMessage, UUID(message_id))
    assert message_record is not None
    assert message_record.body == "Can you help me choose a size?"

    own_list = client.get("/api/v1/messages", headers=customer_headers)
    assert own_list.status_code == 200
    assert own_list.json()["total"] == 1
    assert own_list.json()["items"][0]["id"] == message_id

    own_detail = client.get(f"/api/v1/messages/{message_id}", headers=customer_headers)
    assert own_detail.status_code == 200
    assert own_detail.json()["id"] == message_id

    other_detail = client.get(f"/api/v1/messages/{message_id}", headers=other_headers)
    assert other_detail.status_code == 404

    non_admin_list = client.get("/api/v1/admin/messages", headers=customer_headers)
    assert non_admin_list.status_code == 403

    admin_list = client.get("/api/v1/admin/messages", headers=admin_headers_value)
    assert admin_list.status_code == 200
    assert admin_list.json()["total"] == 1
    assert admin_list.json()["items"][0]["id"] == message_id

    admin_detail = client.get(f"/api/v1/admin/messages/{message_id}", headers=admin_headers_value)
    assert admin_detail.status_code == 200
    assert admin_detail.json()["body"] == "Can you help me choose a size?"

    marked = client.post(f"/api/v1/admin/messages/{message_id}/read", headers=admin_headers_value)
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True
    assert marked.json()["read_at"] is not None

    admin_cannot_send_customer_message = client.post(
        "/api/v1/messages",
        json={"subject": "Admin", "body": "Internal note"},
        headers=admin_headers_value,
    )
    assert admin_cannot_send_customer_message.status_code == 403
    assert admin_cannot_send_customer_message.json()["error"]["code"] == "customer_required"


def test_product_detail_exposes_lowest_active_listing(client: TestClient, db_session: Session) -> None:
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))
    archived_product = db_session.scalar(select(Product).where(Product.slug == "supreme-test-hoodie"))
    assert product is not None
    assert archived_product is not None
    variant = db_session.scalar(select(ProductVariant).where(ProductVariant.product_id == product.id))
    assert variant is not None
    related = create_catalog_product(
        db_session,
        product.category,
        name="Jordan Related Test",
        slug="jordan-related-test",
        brand="Jordan",
        size="11",
        total_sold=3,
    )
    create_store_listing(db_session, related, price_cents=22000)

    higher = create_store_listing(db_session, product, price_cents=26000)
    lower = create_store_listing(db_session, product, product_variant=variant, price_cents=24000)

    detail = client.get("/api/v1/products/jordan-1-retro-high-test")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["lowest_active_listing"]["id"] == str(lower.id)
    assert detail_body["lowest_active_listing"]["price_cents"] == 24000
    assert detail_body["lowest_active_listing"]["available_quantity"] == 10
    assert detail_body["lowest_active_listing"]["status"] == "active"
    assert detail_body["store_price_cents"] == 24000
    assert detail_body["purchase_options"][0]["id"] == str(lower.id)
    assert detail_body["purchase_options"][0]["product_variant_id"] == str(variant.id)
    assert detail_body["purchase_options"][0]["label"] == "10 / Black / J1-TEST-10"
    assert detail_body["stats"]["stock_state"] == "in_stock"
    assert detail_body["stats"]["total_available_quantity"] == 20
    assert "jordan-related-test" in {item["slug"] for item in detail_body["related_products"]}

    lower_model = db_session.get(Listing, lower.id)
    assert lower_model is not None
    lower_model.available_quantity = 0
    db_session.commit()

    detail_after_zero_quantity = client.get("/api/v1/products/jordan-1-retro-high-test")
    assert detail_after_zero_quantity.status_code == 200
    assert detail_after_zero_quantity.json()["lowest_active_listing"]["id"] == str(higher.id)

    higher_model = db_session.get(Listing, higher.id)
    assert higher_model is not None
    higher_model.status = "cancelled"
    db_session.commit()

    detail_without_active = client.get("/api/v1/products/jordan-1-retro-high-test")
    assert detail_without_active.status_code == 200
    detail_without_active_body = detail_without_active.json()
    assert detail_without_active_body["lowest_active_listing"] is None
    assert detail_without_active_body["purchase_options"] == []
    assert detail_without_active_body["stats"]["stock_state"] == "out_of_stock"

    create_store_listing(db_session, archived_product, price_cents=9000)
    archived_product.archived_at = datetime.now(UTC)
    db_session.commit()

    assert client.get("/api/v1/products/supreme-test-hoodie").status_code == 404


def test_listing_management_and_archived_product_rejection(client: TestClient, db_session: Session) -> None:
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))
    archived_product = db_session.scalar(select(Product).where(Product.slug == "supreme-test-hoodie"))
    assert product is not None
    assert archived_product is not None

    assert client.get("/api/v1/listings").status_code == 401

    customer_access, _body = register_user(client, email="listing-customer@example.com")
    customer_headers = {"Authorization": f"Bearer {customer_access}"}
    assert client.get("/api/v1/listings", headers=customer_headers).status_code == 403

    admin_headers_value = admin_headers(client, db_session, email="listing-admin@example.com")
    created = client.post(
        "/api/v1/listings",
        json={"product_id": str(product.id), "price_cents": 25100, "currency": "USD"},
        headers=admin_headers_value,
    )
    assert created.status_code == 201
    listing_id = created.json()["id"]

    admin_owned_list = client.get("/api/v1/listings", headers=admin_headers_value)
    assert admin_owned_list.status_code == 200
    admin_owned_body = admin_owned_list.json()
    assert admin_owned_body["total"] == 1
    assert admin_owned_body["items"][0]["id"] == listing_id
    assert admin_owned_body["items"][0]["user_id"] == created.json()["user_id"]
    assert admin_owned_body["items"][0]["product"]["slug"] == "jordan-1-retro-high-test"
    assert {"id", "user_id", "product", "price_cents", "currency", "status", "created_at", "updated_at"}.issubset(
        admin_owned_body["items"][0].keys()
    )

    customer_cancel = client.post(f"/api/v1/listings/{listing_id}/cancel", headers=customer_headers)
    assert customer_cancel.status_code == 403

    idempotent_cancel = client.post(f"/api/v1/listings/{listing_id}/cancel", headers=admin_headers_value)
    assert idempotent_cancel.status_code == 200
    assert idempotent_cancel.json()["status"] == "cancelled"

    missing_cancel = client.post(f"/api/v1/listings/{uuid4()}/cancel", headers=admin_headers_value)
    assert missing_cancel.status_code == 404

    active_for_admin = client.post(
        "/api/v1/listings",
        json={"product_id": str(product.id), "price_cents": 25200, "currency": "USD"},
        headers=admin_headers_value,
    )
    assert active_for_admin.status_code == 201
    active_listing_id = active_for_admin.json()["id"]
    assert active_for_admin.json()["available_quantity"] == 1

    assert client.get("/api/v1/admin/listings").status_code == 401
    non_admin = client.get("/api/v1/admin/listings", headers=customer_headers)
    assert non_admin.status_code == 403

    admin_active_list = client.get("/api/v1/admin/listings?status=active", headers=admin_headers_value)
    assert admin_active_list.status_code == 200
    assert any(item["id"] == active_listing_id for item in admin_active_list.json()["items"])
    assert all(item["status"] == "active" for item in admin_active_list.json()["items"])
    assert all("available_quantity" in item for item in admin_active_list.json()["items"])

    admin_cancel = client.post(f"/api/v1/admin/listings/{active_listing_id}/cancel", headers=admin_headers_value)
    assert admin_cancel.status_code == 200
    assert admin_cancel.json()["status"] == "cancelled"

    non_admin_cancel = client.post(f"/api/v1/admin/listings/{listing_id}/cancel", headers=customer_headers)
    assert non_admin_cancel.status_code == 403

    archived_product.archived_at = datetime.now(UTC)
    db_session.commit()
    archived_create = client.post(
        "/api/v1/listings",
        json={"product_id": str(archived_product.id), "price_cents": 10000, "currency": "USD"},
        headers=admin_headers_value,
    )
    assert archived_create.status_code == 409
    assert archived_create.json()["error"]["code"] == "product_archived"


def test_supreme_admin_inventory_service_rules(db_session: Session) -> None:
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))
    assert product is not None
    variant = db_session.scalar(select(ProductVariant).where(ProductVariant.product_id == product.id))
    assert variant is not None
    archived_product = db_session.scalar(select(Product).where(Product.slug == "supreme-test-hoodie"))
    assert archived_product is not None

    supreme = User(
        name="Supreme Inventory",
        email="supreme-inventory-service@example.com",
        password_hash=hash_password("password123"),
        is_admin=True,
        is_supreme_admin=True,
    )
    normal_admin = User(
        name="Normal Inventory",
        email="normal-inventory-service@example.com",
        password_hash=hash_password("password123"),
        is_admin=True,
    )
    customer = User(
        name="Customer Inventory",
        email="customer-inventory-service@example.com",
        password_hash=hash_password("password123"),
    )
    listing = Listing(user=supreme, product=product, price_cents=24400, available_quantity=2, currency="USD")
    db_session.add_all([supreme, normal_admin, customer, listing])
    db_session.commit()

    created = listing_service.create_managed_listing(
        db_session,
        actor=supreme,
        product_id=product.id,
        product_variant_id=variant.id,
        price_cents=25500,
        currency="usd",
        available_quantity=4,
        listing_status="active",
    )
    assert created.user_id == supreme.id
    assert created.product_id == product.id
    assert created.product_variant_id == variant.id
    assert created.price_cents == 25500
    assert created.currency == "USD"
    assert created.available_quantity == 4
    assert created.status == "active"

    for actor in (normal_admin, customer):
        with pytest.raises(APIError) as rejected:
            listing_service.create_managed_listing(
                db_session,
                actor=actor,
                product_id=product.id,
                product_variant_id=None,
                price_cents=25500,
                currency="USD",
                available_quantity=1,
                listing_status="active",
            )
        assert rejected.value.code == "supreme_admin_required"

    with pytest.raises(APIError) as missing_product:
        listing_service.create_managed_listing(
            db_session,
            actor=supreme,
            product_id=uuid4(),
            product_variant_id=None,
            price_cents=25500,
            currency="USD",
            available_quantity=1,
            listing_status="active",
        )
    assert missing_product.value.code == "product_not_found"

    archived_product.archived_at = datetime.now(UTC)
    db_session.commit()
    with pytest.raises(APIError) as archived:
        listing_service.create_managed_listing(
            db_session,
            actor=supreme,
            product_id=archived_product.id,
            product_variant_id=None,
            price_cents=25500,
            currency="USD",
            available_quantity=1,
            listing_status="active",
        )
    assert archived.value.code == "product_archived"

    with pytest.raises(APIError) as missing_variant:
        listing_service.create_managed_listing(
            db_session,
            actor=supreme,
            product_id=product.id,
            product_variant_id=uuid4(),
            price_cents=25500,
            currency="USD",
            available_quantity=1,
            listing_status="active",
        )
    assert missing_variant.value.code == "variant_not_found"

    with pytest.raises(APIError) as invalid_quantity:
        listing_service.create_managed_listing(
            db_session,
            actor=supreme,
            product_id=product.id,
            product_variant_id=None,
            price_cents=25500,
            currency="USD",
            available_quantity=-1,
            listing_status="active",
        )
    assert invalid_quantity.value.code == "invalid_available_quantity"

    with pytest.raises(APIError) as invalid_status:
        listing_service.create_managed_listing(
            db_session,
            actor=supreme,
            product_id=product.id,
            product_variant_id=None,
            price_cents=25500,
            currency="USD",
            available_quantity=1,
            listing_status="draft",
        )
    assert invalid_status.value.code == "invalid_listing_status"

    increased = listing_service.adjust_managed_listing_quantity(db_session, listing_id=listing.id, adjustment=3, actor=supreme)
    assert increased.available_quantity == 5
    decreased = listing_service.adjust_managed_listing_quantity(db_session, listing_id=listing.id, adjustment=-2, actor=supreme)
    assert decreased.available_quantity == 3

    with pytest.raises(APIError) as below_zero:
        listing_service.adjust_managed_listing_quantity(db_session, listing_id=listing.id, adjustment=-4, actor=supreme)
    assert below_zero.value.code == "inventory_quantity_below_zero"
    assert db_session.get(Listing, listing.id).available_quantity == 3

    with pytest.raises(APIError) as invalid_adjustment:
        listing_service.adjust_managed_listing_quantity(db_session, listing_id=listing.id, adjustment=0, actor=supreme)
    assert invalid_adjustment.value.code == "invalid_quantity_adjustment"

    with pytest.raises(APIError) as missing_quantity:
        listing_service.adjust_managed_listing_quantity(db_session, listing_id=uuid4(), adjustment=1, actor=supreme)
    assert missing_quantity.value.code == "listing_not_found"

    for actor in (normal_admin, customer):
        with pytest.raises(APIError) as rejected:
            listing_service.adjust_managed_listing_quantity(db_session, listing_id=listing.id, adjustment=1, actor=actor)
        assert rejected.value.code == "supreme_admin_required"

    sold = listing_service.change_managed_listing_status(db_session, listing_id=listing.id, next_status="sold", actor=supreme)
    assert sold.status == "sold"
    cancelled = listing_service.change_managed_listing_status(db_session, listing_id=listing.id, next_status="cancelled", actor=supreme)
    assert cancelled.status == "cancelled"
    active = listing_service.change_managed_listing_status(db_session, listing_id=listing.id, next_status="active", actor=supreme)
    assert active.status == "active"

    with pytest.raises(APIError) as missing_status:
        listing_service.change_managed_listing_status(db_session, listing_id=uuid4(), next_status="sold", actor=supreme)
    assert missing_status.value.code == "listing_not_found"

    for actor in (normal_admin, customer):
        with pytest.raises(APIError) as rejected:
            listing_service.change_managed_listing_status(db_session, listing_id=listing.id, next_status="sold", actor=actor)
        assert rejected.value.code == "supreme_admin_required"


def test_supreme_admin_product_listing_creation_api(client: TestClient, db_session: Session) -> None:
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))
    other_product = db_session.scalar(select(Product).where(Product.slug == "supreme-test-hoodie"))
    assert product is not None
    assert other_product is not None
    variant = db_session.scalar(select(ProductVariant).where(ProductVariant.product_id == product.id))
    assert variant is not None
    other_variant = ProductVariant(product=other_product, size="M", color="Black", sku="HOODIE-M")
    db_session.add(other_variant)
    db_session.commit()

    customer_access, _body = register_user(client, email="create-listing-customer@example.com")
    customer_headers = {"Authorization": f"Bearer {customer_access}"}
    normal_headers = admin_headers(client, db_session, email="create-listing-normal@example.com")
    supreme_headers = supreme_admin_headers(client, db_session, email="create-listing-supreme@example.com")

    payload = {
        "product_variant_id": str(variant.id),
        "price_cents": 23000,
        "currency": "usd",
        "available_quantity": 3,
        "status": "active",
    }

    anonymous = client.post(f"/api/v1/admin/products/{product.id}/listings", json=payload)
    assert anonymous.status_code == 401
    customer = client.post(f"/api/v1/admin/products/{product.id}/listings", json=payload, headers=customer_headers)
    assert customer.status_code == 403
    normal = client.post(f"/api/v1/admin/products/{product.id}/listings", json=payload, headers=normal_headers)
    assert normal.status_code == 403

    invalid_price = client.post(
        f"/api/v1/admin/products/{product.id}/listings",
        json={**payload, "price_cents": 0},
        headers=supreme_headers,
    )
    assert invalid_price.status_code == 422
    invalid_quantity = client.post(
        f"/api/v1/admin/products/{product.id}/listings",
        json={**payload, "available_quantity": -1},
        headers=supreme_headers,
    )
    assert invalid_quantity.status_code == 422
    invalid_currency = client.post(
        f"/api/v1/admin/products/{product.id}/listings",
        json={**payload, "currency": "US1"},
        headers=supreme_headers,
    )
    assert invalid_currency.status_code == 422
    invalid_status = client.post(
        f"/api/v1/admin/products/{product.id}/listings",
        json={**payload, "status": "draft"},
        headers=supreme_headers,
    )
    assert invalid_status.status_code == 422
    mismatched_variant = client.post(
        f"/api/v1/admin/products/{product.id}/listings",
        json={**payload, "product_variant_id": str(other_variant.id)},
        headers=supreme_headers,
    )
    assert mismatched_variant.status_code == 404
    assert mismatched_variant.json()["error"]["code"] == "variant_not_found"

    missing_product = client.post(f"/api/v1/admin/products/{uuid4()}/listings", json=payload, headers=supreme_headers)
    assert missing_product.status_code == 404

    other_product.archived_at = datetime.now(UTC)
    db_session.commit()
    archived = client.post(
        f"/api/v1/admin/products/{other_product.id}/listings",
        json={**payload, "product_variant_id": None},
        headers=supreme_headers,
    )
    assert archived.status_code == 409
    assert archived.json()["error"]["code"] == "product_archived"

    created = client.post(f"/api/v1/admin/products/{product.id}/listings", json=payload, headers=supreme_headers)
    assert created.status_code == 201
    created_body = created.json()
    assert created_body["product_id"] == str(product.id)
    assert created_body["product_variant_id"] == str(variant.id)
    assert created_body["price_cents"] == 23000
    assert created_body["currency"] == "USD"
    assert created_body["available_quantity"] == 3
    assert created_body["status"] == "active"
    assert created_body["product"]["slug"] == "jordan-1-retro-high-test"

    zero_quantity = client.post(
        f"/api/v1/admin/products/{product.id}/listings",
        json={**payload, "product_variant_id": None, "price_cents": 10000, "available_quantity": 0},
        headers=supreme_headers,
    )
    assert zero_quantity.status_code == 201
    sold = client.post(
        f"/api/v1/admin/products/{product.id}/listings",
        json={**payload, "product_variant_id": None, "price_cents": 9000, "available_quantity": 5, "status": "sold"},
        headers=supreme_headers,
    )
    assert sold.status_code == 201

    detail = client.get("/api/v1/products/jordan-1-retro-high-test")
    assert detail.status_code == 200
    assert detail.json()["lowest_active_listing"]["id"] == created_body["id"]
    assert detail.json()["lowest_active_listing"]["available_quantity"] == 3

    buyer_access, _buyer = register_user(client, email="create-listing-buyer@example.com")
    buyer_headers = {"Authorization": f"Bearer {buyer_access}"}
    active_cart = client.post(
        "/api/v1/cart/items",
        json={"listing_id": created_body["id"], "quantity": 3},
        headers=buyer_headers,
    )
    assert active_cart.status_code == 201
    zero_cart = client.post(
        "/api/v1/cart/items",
        json={"listing_id": zero_quantity.json()["id"], "quantity": 1},
        headers=buyer_headers,
    )
    assert zero_cart.status_code == 409
    sold_cart = client.post(
        "/api/v1/cart/items",
        json={"listing_id": sold.json()["id"], "quantity": 1},
        headers=buyer_headers,
    )
    assert sold_cart.status_code == 409

    quantity_updated = client.post(
        f"/api/v1/admin/listings/{created_body['id']}/inventory/quantity",
        json={"adjustment": 2},
        headers=supreme_headers,
    )
    assert quantity_updated.status_code == 200
    assert quantity_updated.json()["available_quantity"] == 5
    status_updated = client.patch(
        f"/api/v1/admin/listings/{created_body['id']}/inventory/status",
        json={"status": "sold"},
        headers=supreme_headers,
    )
    assert status_updated.status_code == 200
    assert status_updated.json()["status"] == "sold"
    reactivated = client.patch(
        f"/api/v1/admin/listings/{created_body['id']}/inventory/status",
        json={"status": "active"},
        headers=supreme_headers,
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "active"

    full_update_payload = {
        "product_variant_id": None,
        "price_cents": 21000,
        "currency": "usd",
        "available_quantity": 4,
        "status": "active",
    }
    normal_update = client.patch(
        f"/api/v1/admin/listings/{created_body['id']}/inventory",
        json=full_update_payload,
        headers=normal_headers,
    )
    assert normal_update.status_code == 403
    invalid_update = client.patch(
        f"/api/v1/admin/listings/{created_body['id']}/inventory",
        json={**full_update_payload, "price_cents": 0},
        headers=supreme_headers,
    )
    assert invalid_update.status_code == 422
    mismatched_update = client.patch(
        f"/api/v1/admin/listings/{created_body['id']}/inventory",
        json={**full_update_payload, "product_variant_id": str(other_variant.id)},
        headers=supreme_headers,
    )
    assert mismatched_update.status_code == 404
    assert mismatched_update.json()["error"]["code"] == "variant_not_found"
    full_update = client.patch(
        f"/api/v1/admin/listings/{created_body['id']}/inventory",
        json=full_update_payload,
        headers=supreme_headers,
    )
    assert full_update.status_code == 200
    assert full_update.json()["product_variant_id"] is None
    assert full_update.json()["price_cents"] == 21000
    assert full_update.json()["currency"] == "USD"
    assert full_update.json()["available_quantity"] == 4

    managed = client.get("/api/v1/admin/products", headers=normal_headers)
    assert managed.status_code == 200
    managed_product = next(item for item in managed.json()["items"] if item["id"] == str(product.id))
    assert managed_product["inventory_summary"]["total_listings"] == 3
    assert managed_product["inventory_summary"]["active_listings"] == 2
    assert managed_product["inventory_summary"]["total_available_quantity"] == 4
    assert managed_product["inventory_summary"]["lowest_active_price_cents"] == 21000
    assert any(
        item["id"] == created_body["id"] and item["available_quantity"] == 4 and item["status"] == "active"
        for item in managed_product["inventory_items"]
    )


def test_supreme_admin_inventory_management_api(client: TestClient, db_session: Session) -> None:
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))
    assert product is not None
    listing = create_store_listing(db_session, product, price_cents=24400, available_quantity=2)
    listing_id = str(listing.id)

    customer_access, _body = register_user(client, email="inventory-api-customer@example.com")
    customer_headers = {"Authorization": f"Bearer {customer_access}"}
    normal_headers = admin_headers(client, db_session, email="inventory-api-normal@example.com")
    supreme_headers = supreme_admin_headers(client, db_session, email="inventory-api-supreme@example.com")

    anonymous = client.post(f"/api/v1/admin/listings/{listing_id}/inventory/quantity", json={"adjustment": 1})
    assert anonymous.status_code == 401
    customer = client.post(
        f"/api/v1/admin/listings/{listing_id}/inventory/quantity",
        json={"adjustment": 1},
        headers=customer_headers,
    )
    assert customer.status_code == 403
    normal = client.post(
        f"/api/v1/admin/listings/{listing_id}/inventory/quantity",
        json={"adjustment": 1},
        headers=normal_headers,
    )
    assert normal.status_code == 403
    db_session.refresh(listing)
    assert listing.available_quantity == 2

    invalid = client.post(
        f"/api/v1/admin/listings/{listing_id}/inventory/quantity",
        json={"adjustment": 0},
        headers=supreme_headers,
    )
    assert invalid.status_code == 422
    below_zero = client.post(
        f"/api/v1/admin/listings/{listing_id}/inventory/quantity",
        json={"adjustment": -3},
        headers=supreme_headers,
    )
    assert below_zero.status_code == 409
    db_session.refresh(listing)
    assert listing.available_quantity == 2

    increased = client.post(
        f"/api/v1/admin/listings/{listing_id}/inventory/quantity",
        json={"adjustment": 4},
        headers=supreme_headers,
    )
    assert increased.status_code == 200
    assert increased.json()["available_quantity"] == 6

    missing = client.post(
        f"/api/v1/admin/listings/{uuid4()}/inventory/quantity",
        json={"adjustment": 1},
        headers=supreme_headers,
    )
    assert missing.status_code == 404

    rejected_status = client.patch(
        f"/api/v1/admin/listings/{listing_id}/inventory/status",
        json={"status": "sold"},
        headers=normal_headers,
    )
    assert rejected_status.status_code == 403
    db_session.refresh(listing)
    assert listing.status == "active"

    sold = client.patch(
        f"/api/v1/admin/listings/{listing_id}/inventory/status",
        json={"status": "sold"},
        headers=supreme_headers,
    )
    assert sold.status_code == 200
    assert sold.json()["status"] == "sold"

    active = client.patch(
        f"/api/v1/admin/listings/{listing_id}/inventory/status",
        json={"status": "active"},
        headers=supreme_headers,
    )
    assert active.status_code == 200
    assert active.json()["status"] == "active"

    managed = client.get("/api/v1/admin/products", headers=normal_headers)
    assert managed.status_code == 200
    managed_product = next(item for item in managed.json()["items"] if item["id"] == str(product.id))
    assert managed_product["inventory_summary"]["total_available_quantity"] >= 6
    assert any(item["id"] == listing_id and item["available_quantity"] == 6 for item in managed_product["inventory_items"])


def test_authenticated_cart_flow_and_user_scoping(client: TestClient, db_session: Session) -> None:
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))
    assert product is not None

    listing = create_store_listing(db_session, product, price_cents=24400)
    listing_id = str(listing.id)

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
    assert added.json()["listing"]["available_quantity"] == 10
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

    excessive_add = client.post(
        "/api/v1/cart/items",
        json={"listing_id": listing_id, "quantity": 6},
        headers=buyer_headers,
    )
    assert excessive_add.status_code == 409
    assert excessive_add.json()["error"]["code"] == "quantity_exceeds_availability"

    excessive_update = client.patch(f"/api/v1/cart/items/{item_id}", json={"quantity": 11}, headers=buyer_headers)
    assert excessive_update.status_code == 409
    assert excessive_update.json()["error"]["code"] == "quantity_exceeds_availability"

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

    existing_listing = db_session.get(Listing, listing.id)
    assert existing_listing is not None
    existing_listing.available_quantity = 3
    db_session.commit()
    quantity_limited_cart = client.get("/api/v1/cart", headers=buyer_headers)
    assert quantity_limited_cart.status_code == 200
    assert quantity_limited_cart.json()["items"][0]["available"] is False
    assert quantity_limited_cart.json()["items"][0]["unavailable_reason"] == "quantity_limited"

    existing_listing.available_quantity = 0
    db_session.commit()
    zero_quantity_add = client.post("/api/v1/cart/items", json={"listing_id": listing_id, "quantity": 1}, headers=buyer_headers)
    assert zero_quantity_add.status_code == 409

    existing_listing.available_quantity = 10
    db_session.commit()

    assert client.post("/api/v1/cart/items", json={"listing_id": str(uuid4())}, headers=buyer_headers).status_code == 404

    inactive_listing = create_store_listing(db_session, product, price_cents=24500)
    inactive_listing_id = str(inactive_listing.id)
    inactive_model = db_session.get(Listing, inactive_listing.id)
    assert inactive_model is not None
    inactive_model.status = "sold"
    db_session.commit()

    inactive_add = client.post("/api/v1/cart/items", json={"listing_id": inactive_listing_id}, headers=buyer_headers)
    assert inactive_add.status_code == 409
    assert inactive_add.json()["error"]["code"] == "listing_unavailable"

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


def test_guest_cart_resolution_and_authenticated_merge(client: TestClient, db_session: Session) -> None:
    product = db_session.scalar(select(Product).where(Product.slug == "jordan-1-retro-high-test"))
    archived_product = db_session.scalar(select(Product).where(Product.slug == "supreme-test-hoodie"))
    assert product is not None
    assert archived_product is not None

    active = create_store_listing(db_session, product, price_cents=24400)
    active_id = str(active.id)
    limited = create_store_listing(db_session, product, price_cents=24600, available_quantity=2)
    limited_id = str(limited.id)

    inactive = create_store_listing(db_session, product, price_cents=24500)
    inactive_id = str(inactive.id)
    inactive_model = db_session.get(Listing, inactive.id)
    assert inactive_model is not None
    inactive_model.status = "sold"

    archived = create_store_listing(db_session, archived_product, price_cents=5700)
    archived_id = str(archived.id)
    archived_product.archived_at = datetime.now(UTC)
    db_session.commit()

    missing_id = str(uuid4())
    invalid = client.post("/api/v1/cart/guest/resolve", json={"items": [{"listing_id": "not-a-uuid", "quantity": 1}]})
    assert invalid.status_code == 422

    resolved = client.post(
        "/api/v1/cart/guest/resolve",
        json={
            "items": [
                {"listing_id": active_id, "quantity": 2},
                {"listing_id": limited_id, "quantity": 3},
                {"listing_id": inactive_id, "quantity": 1},
                {"listing_id": archived_id, "quantity": 1},
                {"listing_id": missing_id, "quantity": 1},
            ]
        },
    )
    assert resolved.status_code == 200
    body = resolved.json()
    assert body["items"][0]["available"] is True
    assert body["items"][0]["listing"]["product"]["slug"] == "jordan-1-retro-high-test"
    assert {item["reason"] for item in body["skipped"]} == {
        "quantity_limited",
        "listing_sold",
        "product_archived",
        "listing_not_found",
    }

    buyer_access, _body = register_user(client, email="guest-cart-buyer@example.com")
    buyer_headers = {"Authorization": f"Bearer {buyer_access}"}
    existing = client.post("/api/v1/cart/items", json={"listing_id": active_id, "quantity": 2}, headers=buyer_headers)
    assert existing.status_code == 201

    assert client.post("/api/v1/cart/merge", json={"items": []}).status_code == 401
    merged = client.post(
        "/api/v1/cart/merge",
        json={
            "items": [
                {"listing_id": active_id, "quantity": 3},
                {"listing_id": inactive_id, "quantity": 1},
                {"listing_id": missing_id, "quantity": 1},
            ]
        },
        headers=buyer_headers,
    )
    assert merged.status_code == 200
    merged_body = merged.json()
    assert merged_body["cart"]["items"][0]["listing_id"] == active_id
    assert merged_body["cart"]["items"][0]["quantity"] == 5
    assert merged_body["cart"]["total_quantity"] == 5
    assert {item["reason"] for item in merged_body["skipped"]} == {"listing_sold", "listing_not_found"}
