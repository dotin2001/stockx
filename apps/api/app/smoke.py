from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from time import time_ns
from uuid import uuid4

import httpx

from app.admin import promote_admin, promote_supreme_admin


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
    try:
        promote_admin(email)
    except Exception as exc:
        fail(f"Could not promote smoke admin {email!r}: {exc}")


def promote_supreme_admin_user(email: str) -> None:
    try:
        promote_supreme_admin(email)
    except Exception as exc:
        fail(f"Could not promote smoke supreme admin {email!r}: {exc}")


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

    discovery_response = request(
        client,
        "GET",
        "/api/v1/search",
        params={"q": SEEDED_SEARCH_QUERY, "brand": "Jordan", "sort": "name_asc"},
    )
    assert_status(discovery_response, 200, "GET /api/v1/search with discovery filters")
    discovery_page = response_json(discovery_response, "filtered discovery search")
    if not isinstance(discovery_page, dict):
        fail("Filtered discovery response should be an object.")
    discovery = discovery_page.get("discovery")
    if not isinstance(discovery, dict):
        fail("Filtered discovery response should include discovery metadata.")
    assert_equal(discovery.get("sort"), "name_asc", "Discovery sort mismatch.")
    selected = discovery.get("selected")
    if not isinstance(selected, dict):
        fail("Discovery metadata should include selected filters.")
    assert_equal(selected.get("q"), SEEDED_SEARCH_QUERY, "Discovery query metadata mismatch.")
    assert_equal(selected.get("brands"), ["Jordan"], "Discovery brand filter metadata mismatch.")
    if not isinstance(discovery.get("brands"), list):
        fail("Discovery metadata should include brand facet options.")
    if not isinstance(discovery.get("sizes"), list):
        fail("Discovery metadata should include size facet options.")
    if not isinstance(discovery.get("price_bounds"), dict):
        fail("Discovery metadata should include price bounds.")
    discovery_slugs = {item.get("slug") for item in discovery_page.get("items", []) if isinstance(item, dict)}
    if SEEDED_PRODUCT_SLUG not in discovery_slugs:
        fail("Filtered discovery search did not include the expected seeded product.")

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


def smoke_protected_marketplace(client: httpx.Client, access_token: str, product_id: str) -> None:
    unauth_listing = request(
        client,
        "POST",
        "/api/v1/listings",
        json={"product_id": product_id, "price_cents": 25000, "currency": "USD"},
    )
    assert_status(unauth_listing, 401, "Unauthenticated POST /api/v1/listings")

    headers = {"Authorization": f"Bearer {access_token}"}
    customer_listing = request(
        client,
        "POST",
        "/api/v1/listings",
        json={"product_id": product_id, "price_cents": 25000, "currency": "USD"},
        headers=headers,
    )
    assert_status(customer_listing, 403, "Customer POST /api/v1/listings")
    require_error_code(response_json(customer_listing, "customer listing creation"), "admin_required", "Customer listing")

    profile = request(
        client,
        "PUT",
        "/api/v1/seller/profile",
        json={
            "phone_number": "+15555550123",
            "address_line1": "123 Market Street",
            "address_line2": "Suite 4",
            "city": "San Francisco",
            "state": "CA",
            "postal_code": "94105",
            "country": "US",
        },
        headers=headers,
    )
    assert_status(profile, 410, "PUT /api/v1/seller/profile")
    require_error_code(response_json(profile, "disabled seller profile"), "seller_flow_disabled", "Seller profile")

    current_user = request(client, "GET", "/api/v1/auth/me", headers=headers)
    assert_status(current_user, 200, "GET /api/v1/auth/me after disabled seller flow")
    if response_json(current_user, "customer current user").get("is_seller") is not False:
        fail("Current user should remain a customer after disabled seller flow.")

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

    message = request(
        client,
        "POST",
        "/api/v1/messages",
        json={"subject": "Smoke question", "body": "Can the store admin help me?"},
        headers=headers,
    )
    assert_status(message, 201, "POST /api/v1/messages")
    message_body = response_json(message, "customer message")
    if not isinstance(message_body, dict) or message_body.get("subject") != "Smoke question":
        fail("Customer message response should include the saved subject.")

    messages = request(client, "GET", "/api/v1/messages", headers=headers)
    assert_status(messages, 200, "GET /api/v1/messages")
    messages_body = response_json(messages, "customer message list")
    if not isinstance(messages_body, dict) or messages_body.get("total", 0) < 1:
        fail("Customer message list should include the sent message.")


def smoke_cart(client: httpx.Client, access_token: str, listing_id: str) -> None:
    unauth_cart = request(client, "GET", "/api/v1/cart")
    assert_status(unauth_cart, 401, "Unauthenticated GET /api/v1/cart")

    guest_resolve = request(
        client,
        "POST",
        "/api/v1/cart/guest/resolve",
        json={"items": [{"listing_id": listing_id, "quantity": 2}]},
    )
    assert_status(guest_resolve, 200, "POST /api/v1/cart/guest/resolve")
    guest_body = response_json(guest_resolve, "guest cart resolve")
    if not isinstance(guest_body, dict) or not isinstance(guest_body.get("items"), list):
        fail("Guest cart resolve response should include an items list.")
    guest_item = guest_body["items"][0]
    if not isinstance(guest_item, dict):
        fail("Guest cart resolve item should be an object.")
    if guest_item.get("available") is not True:
        fail("Guest cart resolve should mark the active listing as available.")
    assert_equal(guest_item.get("listing_id"), listing_id, "Guest cart listing mismatch.")
    assert_equal(guest_item.get("quantity"), 2, "Guest cart quantity mismatch.")
    guest_listing = guest_item.get("listing")
    if not isinstance(guest_listing, dict):
        fail("Guest cart resolve should include listing data for active listings.")
    if not isinstance(guest_listing.get("price_cents"), int):
        fail("Guest cart listing should include price_cents.")
    if not isinstance(guest_listing.get("product"), dict) or not guest_listing["product"].get("slug"):
        fail("Guest cart listing should include product data.")

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

    unauth_merge = request(client, "POST", "/api/v1/cart/merge", json={"items": [{"listing_id": listing_id, "quantity": 1}]})
    assert_status(unauth_merge, 401, "Unauthenticated POST /api/v1/cart/merge")

    merged_guest = request(
        client,
        "POST",
        "/api/v1/cart/merge",
        json={"items": [{"listing_id": listing_id, "quantity": 2}]},
        headers=headers,
    )
    assert_status(merged_guest, 200, "POST /api/v1/cart/merge")
    merged_guest_body = response_json(merged_guest, "guest cart merge")
    if not isinstance(merged_guest_body, dict):
        fail("Guest cart merge response should be an object.")
    merged_cart = merged_guest_body.get("cart")
    if not isinstance(merged_cart, dict) or not isinstance(merged_cart.get("items"), list):
        fail("Guest cart merge response should include a cart items list.")
    assert_equal(merged_cart.get("total_quantity"), 2, "Merged guest cart quantity mismatch.")


def smoke_checkout_orders(client: httpx.Client, access_token: str, listing_id: str) -> None:
    headers = {"Authorization": f"Bearer {access_token}"}
    summary_response = request(client, "GET", "/api/v1/checkout/summary", headers=headers)
    assert_status(summary_response, 200, "GET /api/v1/checkout/summary")
    summary = response_json(summary_response, "checkout summary")
    if not isinstance(summary, dict):
        fail("Checkout summary should be an object.")
    if summary.get("order_placement_enabled") is not True:
        fail(
            "Manual checkout is disabled. Start the API with CHECKOUT_MODE=manual "
            "before running the checkout/order smoke workflow."
        )
    checkout_token = summary.get("checkout_token")
    if not isinstance(checkout_token, str) or not checkout_token:
        fail("Checkout summary should include a checkout token.")
    summary_items = summary.get("items")
    if not isinstance(summary_items, list) or len(summary_items) != 1:
        fail("Checkout summary should include the cart line prepared by the smoke workflow.")
    assert_equal(summary_items[0].get("listing_id"), listing_id, "Checkout listing mismatch.")

    created_response = request(
        client,
        "POST",
        "/api/v1/orders",
        headers={**headers, "Idempotency-Key": f"smoke-{uuid4()}"},
        json={
            "checkout_token": checkout_token,
            "shipping": {
                "recipient_name": "API Smoke User",
                "contact_email": "smoke-order@example.test",
                "contact_phone": "+1 555 555 0101",
                "address_line1": "123 Smoke Test Way",
                "address_line2": None,
                "city": "San Francisco",
                "state": "CA",
                "postal_code": "94105",
                "country": "US",
            },
        },
    )
    assert_status(created_response, 201, "POST /api/v1/orders")
    created = response_json(created_response, "created order")
    if not isinstance(created, dict):
        fail("Created order should be an object.")
    order_id = created.get("id")
    if not isinstance(order_id, str) or not order_id:
        fail("Created order should include an id.")
    assert_equal(created.get("status"), "confirmed", "Created order status mismatch.")
    assert_equal(created.get("payment_status"), "unpaid", "Created order payment status mismatch.")
    if not isinstance(created.get("items"), list) or created["items"][0].get("listing_id") != listing_id:
        fail("Created order should preserve the purchased listing snapshot.")

    cart_after = request(client, "GET", "/api/v1/cart", headers=headers)
    assert_status(cart_after, 200, "GET /api/v1/cart after checkout")
    cart_body = response_json(cart_after, "cart after checkout")
    if not isinstance(cart_body, dict):
        fail("Cart after checkout should be an object.")
    assert_equal(cart_body.get("items"), [], "Checkout should clear purchased cart rows.")

    history_response = request(client, "GET", "/api/v1/orders", headers=headers)
    assert_status(history_response, 200, "GET /api/v1/orders")
    history = response_json(history_response, "order history")
    if not isinstance(history, dict) or not any(item.get("id") == order_id for item in history.get("items", []) if isinstance(item, dict)):
        fail("Created order was not visible in customer order history.")

    detail_response = request(client, "GET", f"/api/v1/orders/{order_id}", headers=headers)
    assert_status(detail_response, 200, "GET /api/v1/orders/{id}")
    detail = response_json(detail_response, "order detail")
    if not isinstance(detail, dict) or detail.get("shipping", {}).get("city") != "San Francisco":
        fail("Order detail should preserve the shipping snapshot.")

    other_token, _refresh = smoke_auth(client, unique_user())
    hidden = request(
        client,
        "GET",
        f"/api/v1/orders/{order_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert_status(hidden, 404, "Cross-user GET /api/v1/orders/{id}")


def smoke_admin_product_management(client: httpx.Client, product_id: str) -> str:
    admin = unique_admin_user()
    admin_token, _refresh_token = smoke_auth(client, admin)
    promote_admin_user(admin.email)
    promote_supreme_admin_user(admin.email)
    headers = {"Authorization": f"Bearer {admin_token}"}

    active_listing = request(
        client,
        "POST",
        "/api/v1/listings",
        json={"product_id": product_id, "price_cents": 25000, "currency": "USD"},
        headers=headers,
    )
    assert_status(active_listing, 201, "Admin POST /api/v1/listings")
    active_listing_body = response_json(active_listing, "admin listing creation")
    if not isinstance(active_listing_body, dict):
        fail("Admin listing response should be an object.")
    active_listing_id = active_listing_body.get("id")
    if not isinstance(active_listing_id, str) or not active_listing_id:
        fail("Admin listing creation should return a listing id.")

    admin_owned_list = request(client, "GET", "/api/v1/listings", headers=headers)
    assert_status(admin_owned_list, 200, "Admin GET /api/v1/listings")
    admin_owned_body = response_json(admin_owned_list, "admin-owned listing list")
    if not isinstance(admin_owned_body, dict) or not isinstance(admin_owned_body.get("items"), list):
        fail("Admin-owned listing list response should include an items list.")
    if not any(item.get("id") == active_listing_id for item in admin_owned_body["items"] if isinstance(item, dict)):
        fail("Admin-created listing was not visible in the admin-owned listing list.")

    cancel_candidate = request(
        client,
        "POST",
        "/api/v1/listings",
        json={"product_id": product_id, "price_cents": 26000, "currency": "USD"},
        headers=headers,
    )
    assert_status(cancel_candidate, 201, "Admin POST /api/v1/listings for cancellation")
    cancel_candidate_body = response_json(cancel_candidate, "admin listing cancellation candidate")
    if not isinstance(cancel_candidate_body, dict):
        fail("Cancellation candidate listing response should be an object.")
    cancel_listing_id = cancel_candidate_body.get("id")
    if not isinstance(cancel_listing_id, str) or not cancel_listing_id:
        fail("Cancellation candidate should return a listing id.")

    cancelled = request(client, "POST", f"/api/v1/listings/{cancel_listing_id}/cancel", headers=headers)
    assert_status(cancelled, 200, "Admin POST /api/v1/listings/{id}/cancel")
    cancelled_body = response_json(cancelled, "admin listing cancel")
    if not isinstance(cancelled_body, dict):
        fail("Admin listing cancel response should be an object.")
    assert_equal(cancelled_body.get("status"), "cancelled", "Admin listing cancel status mismatch.")

    products = request(client, "GET", "/api/v1/admin/products", params={"limit": 20, "offset": 0}, headers=headers)
    assert_status(products, 200, "GET /api/v1/admin/products")
    products_body = response_json(products, "admin product list")
    if not isinstance(products_body, dict) or not isinstance(products_body.get("items"), list):
        fail("Admin product list response should include an items list.")
    admin_product = next((item for item in products_body["items"] if isinstance(item, dict) and item.get("id") == product_id), None)
    if admin_product is None:
        fail("Seeded product was not visible in the admin product list.")
    category = admin_product.get("category")
    if not isinstance(category, dict) or not isinstance(category.get("id"), str):
        fail("Admin product should include category data for product updates.")
    variants = admin_product.get("variants")
    if not isinstance(variants, list):
        fail("Admin product should include variants for stock assignment.")
    variant_id = next((variant.get("id") for variant in variants if isinstance(variant, dict) and isinstance(variant.get("id"), str)), None)

    storefront_payload = {
        "category_id": category["id"],
        "description": "Smoke-tested storefront content.",
        "feature_bullets": ["Smoke-tested feature", "Ready from store stock"],
        "detail_rows": [{"label": "Smoke", "value": "Verified"}],
        "gallery_images": [{"url": "https://example.com/smoke-product.jpg", "alt": "Smoke product"}],
    }
    updated_product = request(
        client,
        "PATCH",
        f"/api/v1/admin/products/{product_id}",
        json=storefront_payload,
        headers=headers,
    )
    assert_status(updated_product, 200, "PATCH /api/v1/admin/products/{id} storefront content")
    updated_product_body = response_json(updated_product, "admin product storefront update")
    if not isinstance(updated_product_body, dict):
        fail("Admin product storefront update response should be an object.")
    assert_equal(updated_product_body.get("feature_bullets"), storefront_payload["feature_bullets"], "Admin product feature bullets mismatch.")
    if updated_product_body.get("detail_rows") != storefront_payload["detail_rows"]:
        fail("Admin product detail rows were not persisted.")
    if updated_product_body.get("gallery_images") != storefront_payload["gallery_images"]:
        fail("Admin product gallery images were not persisted.")

    inventory_update = request(
        client,
        "PATCH",
        f"/api/v1/admin/listings/{active_listing_id}/inventory",
        json={
            "product_variant_id": variant_id,
            "price_cents": 24000,
            "currency": "USD",
            "available_quantity": 3,
            "status": "active",
        },
        headers=headers,
    )
    assert_status(inventory_update, 200, "PATCH /api/v1/admin/listings/{id}/inventory")
    inventory_update_body = response_json(inventory_update, "admin stock update")
    if not isinstance(inventory_update_body, dict):
        fail("Admin stock update response should be an object.")
    assert_equal(inventory_update_body.get("price_cents"), 24000, "Admin stock price update mismatch.")
    assert_equal(inventory_update_body.get("available_quantity"), 3, "Admin stock quantity update mismatch.")
    assert_equal(inventory_update_body.get("status"), "active", "Admin stock status update mismatch.")
    assert_equal(inventory_update_body.get("product_variant_id"), variant_id, "Admin stock variant assignment mismatch.")

    listings = request(client, "GET", "/api/v1/admin/listings", params={"status": "active"}, headers=headers)
    assert_status(listings, 200, "GET /api/v1/admin/listings")
    listings_body = response_json(listings, "admin listing list")
    if not isinstance(listings_body, dict) or not isinstance(listings_body.get("items"), list):
        fail("Admin listing list response should include an items list.")
    if not any(item.get("id") == active_listing_id for item in listings_body["items"] if isinstance(item, dict)):
        fail("Active smoke listing was not visible in the admin listing list.")

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

        archived_listing = request(
            client,
            "POST",
            "/api/v1/listings",
            json={"product_id": product_id, "price_cents": 27000, "currency": "USD"},
            headers=headers,
        )
        assert_status(archived_listing, 409, "POST /api/v1/listings for archived product")
        require_error_code(response_json(archived_listing, "archived product listing"), "product_archived", "Archived listing")
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
    visible_detail_body = response_json(visible_detail, "restored product detail")
    if not isinstance(visible_detail_body, dict):
        fail("Restored product detail response should be an object.")
    assert_equal(visible_detail_body.get("feature_bullets"), storefront_payload["feature_bullets"], "Public product feature bullets mismatch.")
    if visible_detail_body.get("detail_rows") != storefront_payload["detail_rows"]:
        fail("Public product detail rows were not exposed.")
    if visible_detail_body.get("gallery_images") != storefront_payload["gallery_images"]:
        fail("Public product gallery images were not exposed.")
    purchase_options = visible_detail_body.get("purchase_options")
    if not isinstance(purchase_options, list):
        fail("Public product detail should include purchase options.")
    selected_option = next((option for option in purchase_options if isinstance(option, dict) and option.get("id") == active_listing_id), None)
    if selected_option is None:
        fail("Public product detail did not expose the updated stock record as a purchase option.")
    assert_equal(selected_option.get("price_cents"), 24000, "Public purchase option price mismatch.")
    assert_equal(selected_option.get("available_quantity"), 3, "Public purchase option quantity mismatch.")
    assert_equal(selected_option.get("is_available"), True, "Public purchase option should be available.")
    if variant_id is not None:
        assert_equal(selected_option.get("product_variant_id"), variant_id, "Public purchase option variant mismatch.")
    if visible_detail_body.get("store_price_cents") != 24000:
        fail("Public product detail should expose updated store_price_cents.")
    if not isinstance(visible_detail_body.get("stats"), dict):
        fail("Public product detail should include product stats.")
    if not isinstance(visible_detail_body.get("related_products"), list):
        fail("Public product detail should include related products.")

    return active_listing_id


def run_smoke(base_url: str, timeout: float) -> None:
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout) as client:
        product_id = smoke_public_api(client)
        user = unique_user()
        access_token, _refresh_token = smoke_auth(client, user)
        listing_id = smoke_admin_product_management(client, product_id)
        smoke_protected_marketplace(client, access_token, product_id)
        smoke_cart(client, access_token, listing_id)
        smoke_checkout_orders(client, access_token, listing_id)


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
