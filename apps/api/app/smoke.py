from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from time import time_ns
from uuid import uuid4

import httpx
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import User


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
BASE_URL_ENV = "STOCKX_API_BASE_URL"
REFRESH_COOKIE_NAME = "stockx_refresh"
SEEDED_CATEGORY_SLUGS = {"sneakers", "streetwear", "collectibles"}
SEEDED_PRODUCT_SLUG = "jordan-1-retro-high-element-gore-tex-black-particle-grey"
SEEDED_SEARCH_QUERY = "jordan"


class SmokeFailure(AssertionError):
    pass


@dataclass(frozen=True)
class SmokeUser:
    name: str
    email: str
    password: str


def fail(message: str) -> None:
    raise SmokeFailure(message)


def assert_equal(actual: object, expected: object, message: str) -> None:
    if actual != expected:
        fail(f"{message} Expected {expected!r}, got {actual!r}.")


def assert_status(response: httpx.Response, expected: int, context: str) -> None:
    if response.status_code != expected:
        fail(
            f"{context} returned HTTP {response.status_code}, expected {expected}. "
            f"Response body: {response.text[:500]}"
        )


def response_json(response: httpx.Response, context: str) -> dict | list:
    try:
        return response.json()
    except ValueError as exc:
        fail(f"{context} did not return valid JSON. Response body: {response.text[:500]}")
        raise exc


def request(client: httpx.Client, method: str, path: str, **kwargs: object) -> httpx.Response:
    try:
        return client.request(method, path, **kwargs)
    except httpx.ConnectError as exc:
        fail(
            f"Could not connect to API at {client.base_url}. Start the service first, "
            "for example: uvicorn app.main:app --reload"
        )
        raise exc
    except httpx.TimeoutException as exc:
        fail(f"Timed out calling {client.base_url}{path}. Check that the API service is healthy.")
        raise exc
    except httpx.RequestError as exc:
        fail(f"Request to {client.base_url}{path} failed: {exc}")
        raise exc


def unique_user() -> SmokeUser:
    suffix = f"{time_ns()}-{uuid4().hex[:8]}"
    return SmokeUser(
        name="API Smoke User",
        email=f"api-smoke-{suffix}@example.test",
        password="smoke-password-123",
    )


def unique_admin_user() -> SmokeUser:
    user = unique_user()
    return SmokeUser(name="API Smoke Admin", email=user.email.replace("api-smoke-", "api-smoke-admin-", 1), password=user.password)


def promote_admin_user(email: str) -> None:
    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == email))
        if user is None:
            fail(f"Could not promote smoke admin {email!r}; user was not found in the configured database.")
        user.is_admin = True
        session.commit()


def require_error_code(body: dict | list, code: str, context: str) -> None:
    if not isinstance(body, dict):
        fail(f"{context} error response should be an object.")
    actual = body.get("error", {}).get("code")
    assert_equal(actual, code, f"{context} error code mismatch.")


def smoke_public_api(client: httpx.Client) -> str:
    health = request(client, "GET", "/health")
    assert_status(health, 200, "GET /health")
    assert_equal(response_json(health, "GET /health"), {"status": "ok"}, "Health payload mismatch.")

    categories_response = request(client, "GET", "/api/v1/categories")
    assert_status(categories_response, 200, "GET /api/v1/categories")
    categories = response_json(categories_response, "GET /api/v1/categories")
    if not isinstance(categories, list):
        fail("Categories response should be a list.")
    category_slugs = {category.get("slug") for category in categories if isinstance(category, dict)}
    missing_categories = SEEDED_CATEGORY_SLUGS - category_slugs
    if missing_categories:
        fail(
            "Seeded categories are missing. Run migrations and seed data first: "
            "alembic upgrade head && python -m app.db.seed. "
            f"Missing: {sorted(missing_categories)}"
        )

    products_response = request(client, "GET", "/api/v1/products", params={"limit": 20, "offset": 0})
    assert_status(products_response, 200, "GET /api/v1/products")
    products_page = response_json(products_response, "GET /api/v1/products")
    if not isinstance(products_page, dict) or not isinstance(products_page.get("items"), list):
        fail("Products response should include an items list.")
    products = products_page["items"]
    product = next((item for item in products if item.get("slug") == SEEDED_PRODUCT_SLUG), None)
    if product is None:
        fail(
            "Seeded Jordan product is missing from product listing. "
            "Run python -m app.db.seed before the smoke test."
        )
    for field in ("id", "slug", "name", "category", "image_url", "lowest_ask_cents", "total_sold"):
        if field not in product:
            fail(f"Product summary is missing expected field {field!r}.")
    assert_equal(product["category"]["slug"], "sneakers", "Seeded product category mismatch.")

    detail_response = request(client, "GET", f"/api/v1/products/{SEEDED_PRODUCT_SLUG}")
    assert_status(detail_response, 200, f"GET /api/v1/products/{SEEDED_PRODUCT_SLUG}")
    detail = response_json(detail_response, "GET product detail")
    if not isinstance(detail, dict):
        fail("Product detail response should be an object.")
    assert_equal(detail.get("slug"), SEEDED_PRODUCT_SLUG, "Product detail slug mismatch.")
    if "variants" not in detail or not isinstance(detail["variants"], list):
        fail("Product detail should include a variants list.")

    search_response = request(client, "GET", "/api/v1/search", params={"q": SEEDED_SEARCH_QUERY})
    assert_status(search_response, 200, "GET /api/v1/search")
    search_page = response_json(search_response, "GET /api/v1/search")
    if not isinstance(search_page, dict) or not search_page.get("items"):
        fail("Search should return seeded matching products.")
    search_slugs = {item.get("slug") for item in search_page["items"] if isinstance(item, dict)}
    if SEEDED_PRODUCT_SLUG not in search_slugs:
        fail(f"Search did not return expected seeded product {SEEDED_PRODUCT_SLUG!r}.")

    invalid_search = request(client, "GET", "/api/v1/search", params={"q": ""})
    assert_status(invalid_search, 422, "GET /api/v1/search?q=")
    require_error_code(response_json(invalid_search, "empty search"), "validation_error", "Empty search")

    return product["id"]


def assert_refresh_cookie_present(client: httpx.Client, context: str) -> str:
    token = client.cookies.get(REFRESH_COOKIE_NAME)
    if not token:
        fail(f"{context} did not set the {REFRESH_COOKIE_NAME!r} refresh cookie.")
    return token


def smoke_auth(client: httpx.Client, user: SmokeUser) -> tuple[str, str]:
    register = request(
        client,
        "POST",
        "/api/v1/auth/register",
        json={"name": user.name, "email": user.email, "password": user.password},
    )
    assert_status(register, 201, "POST /api/v1/auth/register")
    register_body = response_json(register, "registration")
    if not isinstance(register_body, dict):
        fail("Registration response should be an object.")
    access_token = register_body.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        fail("Registration should return a bearer access token.")
    assert_equal(register_body.get("token_type"), "bearer", "Registration token type mismatch.")
    assert_equal(register_body.get("user", {}).get("email"), user.email, "Registered user email mismatch.")
    registered_refresh = assert_refresh_cookie_present(client, "Registration")

    login = request(
        client,
        "POST",
        "/api/v1/auth/login",
        json={"email": user.email, "password": user.password},
    )
    assert_status(login, 200, "POST /api/v1/auth/login")
    login_body = response_json(login, "login")
    if not isinstance(login_body, dict):
        fail("Login response should be an object.")
    access_token = login_body.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        fail("Login should return a bearer access token.")
    assert_equal(login_body.get("user", {}).get("email"), user.email, "Login user email mismatch.")
    assert_refresh_cookie_present(client, "Login")

    me = request(client, "GET", "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert_status(me, 200, "GET /api/v1/auth/me")
    me_body = response_json(me, "current user")
    if not isinstance(me_body, dict):
        fail("Current user response should be an object.")
    assert_equal(me_body.get("email"), user.email, "Current user email mismatch.")

    old_refresh = client.cookies.get(REFRESH_COOKIE_NAME)
    refresh = request(client, "POST", "/api/v1/auth/refresh")
    assert_status(refresh, 200, "POST /api/v1/auth/refresh")
    refresh_body = response_json(refresh, "refresh")
    if not isinstance(refresh_body, dict):
        fail("Refresh response should be an object.")
    refreshed_access_token = refresh_body.get("access_token")
    if not isinstance(refreshed_access_token, str) or not refreshed_access_token:
        fail("Refresh should return a new bearer access token.")
    new_refresh = assert_refresh_cookie_present(client, "Refresh")
    if new_refresh == old_refresh:
        fail("Refresh should rotate the refresh cookie value.")

    replay = request(client, "POST", "/api/v1/auth/refresh", cookies={REFRESH_COOKIE_NAME: old_refresh})
    assert_status(replay, 401, "Replay old refresh token")

    logout = request(client, "POST", "/api/v1/auth/logout")
    assert_status(logout, 204, "POST /api/v1/auth/logout")
    if client.cookies.get(REFRESH_COOKIE_NAME):
        fail("Logout should clear the refresh cookie.")

    reuse_logged_out_session = request(
        client,
        "POST",
        "/api/v1/auth/refresh",
        cookies={REFRESH_COOKIE_NAME: new_refresh},
    )
    assert_status(reuse_logged_out_session, 401, "Refresh after logout")

    if registered_refresh == new_refresh:
        fail("Smoke sanity check expected refresh rotation across the auth flow.")

    marketplace_login = request(
        client,
        "POST",
        "/api/v1/auth/login",
        json={"email": user.email, "password": user.password},
    )
    assert_status(marketplace_login, 200, "POST /api/v1/auth/login after logout")
    marketplace_login_body = response_json(marketplace_login, "marketplace login")
    if not isinstance(marketplace_login_body, dict):
        fail("Marketplace login response should be an object.")
    marketplace_access_token = marketplace_login_body.get("access_token")
    if not isinstance(marketplace_access_token, str) or not marketplace_access_token:
        fail("Marketplace login should return a bearer access token.")
    assert_refresh_cookie_present(client, "Marketplace login")

    if refreshed_access_token == marketplace_access_token:
        fail("Marketplace login should issue a fresh access token.")

    return marketplace_access_token, new_refresh


def smoke_protected_marketplace(client: httpx.Client, access_token: str, product_id: str) -> str:
    unauth_listing = request(
        client,
        "POST",
        "/api/v1/listings",
        json={"product_id": product_id, "price_cents": 25000, "currency": "USD"},
    )
    assert_status(unauth_listing, 401, "Unauthenticated POST /api/v1/listings")

    headers = {"Authorization": f"Bearer {access_token}"}
    listing = request(
        client,
        "POST",
        "/api/v1/listings",
        json={"product_id": product_id, "price_cents": 25000, "currency": "USD"},
        headers=headers,
    )
    assert_status(listing, 201, "Authenticated POST /api/v1/listings")
    listing_body = response_json(listing, "listing creation")
    if not isinstance(listing_body, dict):
        fail("Listing response should be an object.")
    listing_id = listing_body.get("id")
    if not isinstance(listing_id, str) or not listing_id:
        fail("Listing creation should return a listing id.")
    assert_equal(listing_body.get("product_id"), product_id, "Listing product mismatch.")
    assert_equal(listing_body.get("status"), "active", "Listing status mismatch.")

    watched = request(client, "POST", "/api/v1/watchlist", json={"product_id": product_id}, headers=headers)
    assert_status(watched, 201, "POST /api/v1/watchlist")
    watched_body = response_json(watched, "watchlist add")
    if not isinstance(watched_body, dict):
        fail("Watchlist add response should be an object.")
    watchlist_item_id = watched_body.get("id")
    if not isinstance(watchlist_item_id, str) or not watchlist_item_id:
        fail("Watchlist add should return an item id.")
    assert_equal(watched_body.get("product", {}).get("id"), product_id, "Watched product mismatch.")

    duplicate = request(client, "POST", "/api/v1/watchlist", json={"product_id": product_id}, headers=headers)
    assert_status(duplicate, 409, "Duplicate POST /api/v1/watchlist")
    require_error_code(response_json(duplicate, "duplicate watchlist add"), "watchlist_duplicate", "Duplicate watchlist")

    listed = request(client, "GET", "/api/v1/watchlist", headers=headers)
    assert_status(listed, 200, "GET /api/v1/watchlist")
    listed_body = response_json(listed, "watchlist list")
    if not isinstance(listed_body, list):
        fail("Watchlist list response should be a list.")
    if not any(item.get("id") == watchlist_item_id for item in listed_body if isinstance(item, dict)):
        fail("Created watchlist item was not visible in the authenticated user's watchlist.")

    deleted = request(client, "DELETE", f"/api/v1/watchlist/{watchlist_item_id}", headers=headers)
    assert_status(deleted, 204, "DELETE /api/v1/watchlist/{id}")

    listed_after_delete = request(client, "GET", "/api/v1/watchlist", headers=headers)
    assert_status(listed_after_delete, 200, "GET /api/v1/watchlist after delete")
    after_delete_body = response_json(listed_after_delete, "watchlist list after delete")
    if not isinstance(after_delete_body, list):
        fail("Watchlist list response after delete should be a list.")
    if any(item.get("id") == watchlist_item_id for item in after_delete_body if isinstance(item, dict)):
        fail("Deleted watchlist item is still visible.")

    return listing_id


def smoke_cart(client: httpx.Client, access_token: str, listing_id: str) -> None:
    unauth_cart = request(client, "GET", "/api/v1/cart")
    assert_status(unauth_cart, 401, "Unauthenticated GET /api/v1/cart")

    headers = {"Authorization": f"Bearer {access_token}"}
    empty = request(client, "GET", "/api/v1/cart", headers=headers)
    assert_status(empty, 200, "GET /api/v1/cart")
    empty_body = response_json(empty, "empty cart")
    if not isinstance(empty_body, dict):
        fail("Cart response should be an object.")
    assert_equal(empty_body.get("total_quantity"), 0, "Empty cart quantity mismatch.")
    assert_equal(empty_body.get("items"), [], "Empty cart items mismatch.")

    added = request(client, "POST", "/api/v1/cart/items", json={"listing_id": listing_id, "quantity": 2}, headers=headers)
    assert_status(added, 201, "POST /api/v1/cart/items")
    added_body = response_json(added, "cart add")
    if not isinstance(added_body, dict):
        fail("Cart add response should be an object.")
    cart_item_id = added_body.get("id")
    if not isinstance(cart_item_id, str) or not cart_item_id:
        fail("Cart add should return an item id.")
    assert_equal(added_body.get("listing_id"), listing_id, "Cart listing mismatch.")
    assert_equal(added_body.get("quantity"), 2, "Cart quantity mismatch.")
    assert_equal(added_body.get("available"), True, "Cart item should be available.")

    merged = request(client, "POST", "/api/v1/cart/items", json={"listing_id": listing_id, "quantity": 1}, headers=headers)
    assert_status(merged, 201, "Duplicate POST /api/v1/cart/items")
    merged_body = response_json(merged, "cart merge")
    if not isinstance(merged_body, dict):
        fail("Cart merge response should be an object.")
    assert_equal(merged_body.get("id"), cart_item_id, "Duplicate cart add should merge the existing item.")
    assert_equal(merged_body.get("quantity"), 3, "Merged cart quantity mismatch.")

    listed = request(client, "GET", "/api/v1/cart", headers=headers)
    assert_status(listed, 200, "GET /api/v1/cart after add")
    listed_body = response_json(listed, "cart list")
    if not isinstance(listed_body, dict) or not isinstance(listed_body.get("items"), list):
        fail("Cart list response should include an items list.")
    assert_equal(listed_body.get("total_quantity"), 3, "Cart total quantity mismatch.")
    if not any(item.get("id") == cart_item_id for item in listed_body["items"] if isinstance(item, dict)):
        fail("Created cart item was not visible in the authenticated user's cart.")

    deleted = request(client, "DELETE", f"/api/v1/cart/items/{cart_item_id}", headers=headers)
    assert_status(deleted, 204, "DELETE /api/v1/cart/items/{id}")

    after_delete = request(client, "GET", "/api/v1/cart", headers=headers)
    assert_status(after_delete, 200, "GET /api/v1/cart after delete")
    after_delete_body = response_json(after_delete, "cart list after delete")
    if not isinstance(after_delete_body, dict):
        fail("Cart list response after delete should be an object.")
    assert_equal(after_delete_body.get("total_quantity"), 0, "Cart quantity should be zero after delete.")


def smoke_admin_product_management(client: httpx.Client, product_id: str) -> None:
    admin = unique_admin_user()
    admin_token, _refresh_token = smoke_auth(client, admin)
    promote_admin_user(admin.email)
    headers = {"Authorization": f"Bearer {admin_token}"}

    products = request(client, "GET", "/api/v1/admin/products", params={"limit": 20, "offset": 0}, headers=headers)
    assert_status(products, 200, "GET /api/v1/admin/products")
    products_body = response_json(products, "admin product list")
    if not isinstance(products_body, dict) or not isinstance(products_body.get("items"), list):
        fail("Admin product list response should include an items list.")
    if not any(item.get("id") == product_id for item in products_body["items"] if isinstance(item, dict)):
        fail("Seeded product was not visible in the admin product list.")

    archived = False
    try:
        archive = request(client, "POST", f"/api/v1/admin/products/{product_id}/archive", headers=headers)
        assert_status(archive, 200, "POST /api/v1/admin/products/{id}/archive")
        archive_body = response_json(archive, "admin product archive")
        if not isinstance(archive_body, dict):
            fail("Admin archive response should be an object.")
        if archive_body.get("archived_at") is None:
            fail("Admin archive response should include archived_at.")
        archived = True

        hidden_detail = request(client, "GET", f"/api/v1/products/{SEEDED_PRODUCT_SLUG}")
        assert_status(hidden_detail, 404, "GET archived product detail")
    finally:
        if archived:
            restore = request(client, "POST", f"/api/v1/admin/products/{product_id}/restore", headers=headers)
            assert_status(restore, 200, "POST /api/v1/admin/products/{id}/restore")
            restore_body = response_json(restore, "admin product restore")
            if not isinstance(restore_body, dict):
                fail("Admin restore response should be an object.")
            assert_equal(restore_body.get("archived_at"), None, "Admin restore should clear archived_at.")

    visible_detail = request(client, "GET", f"/api/v1/products/{SEEDED_PRODUCT_SLUG}")
    assert_status(visible_detail, 200, "GET restored product detail")


def run_smoke(base_url: str, timeout: float) -> None:
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout) as client:
        product_id = smoke_public_api(client)
        user = unique_user()
        access_token, _refresh_token = smoke_auth(client, user)
        listing_id = smoke_protected_marketplace(client, access_token, product_id)
        smoke_cart(client, access_token, listing_id)
        smoke_admin_product_management(client, product_id)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run HTTP smoke tests against the StockX FastAPI service.")
    parser.add_argument(
        "--base-url",
        default=os.getenv(BASE_URL_ENV, DEFAULT_BASE_URL),
        help=f"API base URL. Defaults to ${BASE_URL_ENV} or {DEFAULT_BASE_URL}.",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP request timeout in seconds.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        run_smoke(args.base_url, args.timeout)
    except SmokeFailure as exc:
        print(f"FAIL api smoke: {exc}", file=sys.stderr)
        return 1

    print(f"PASS api smoke against {args.base_url.rstrip('/')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
