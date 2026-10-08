from __future__ import annotations

import hashlib
import hmac
import json
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.errors import APIError
from app.core.config import CheckoutMode, settings
from app.models import CartItem, Listing, Product, User
from app.schemas.order import CheckoutItemRead, CheckoutSummary


CHECKOUT_LOAD_OPTIONS = (
    selectinload(CartItem.listing).selectinload(Listing.product_variant),
    selectinload(CartItem.listing).selectinload(Listing.product),
)


def variant_label(listing: Listing) -> str | None:
    variant = listing.product_variant
    if variant is None:
        return None
    parts = [part for part in (variant.size, variant.color) if part]
    return " / ".join(parts) or variant.sku


def _cart_items(db: Session, user_id: UUID, *, lock: bool = False) -> list[CartItem]:
    query = (
        select(CartItem)
        .where(CartItem.user_id == user_id)
        .options(*CHECKOUT_LOAD_OPTIONS)
        .order_by(CartItem.id)
        .execution_options(populate_existing=True)
    )
    if lock:
        query = query.with_for_update()
    return list(db.scalars(query).all())


def checkout_token_for_items(*, user_id: UUID, items: list[CartItem], secret: str) -> str:
    state = {
        "user_id": str(user_id),
        "items": [
            {
                "cart_item_id": str(item.id),
                "listing_id": str(item.listing_id),
                "product_id": str(item.listing.product_id),
                "product_variant_id": str(item.listing.product_variant_id) if item.listing.product_variant_id else None,
                "quantity": item.quantity,
                "unit_price_cents": item.listing.price_cents,
                "currency": item.listing.currency.upper(),
                "listing_status": item.listing.status,
                "available_quantity": item.listing.available_quantity,
                "product_archived": item.listing.product.archived_at is not None,
            }
            for item in sorted(items, key=lambda row: str(row.id))
        ],
    }
    encoded = json.dumps(state, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), encoded, hashlib.sha256).hexdigest()


def _validate_items(items: list[CartItem]) -> str:
    if not items:
        raise APIError(status.HTTP_409_CONFLICT, "cart_empty", "Your cart is empty.")
    currencies: set[str] = set()
    for item in items:
        listing = item.listing
        if listing.product.archived_at is not None:
            raise APIError(status.HTTP_409_CONFLICT, "product_archived", "A product in your cart is no longer available.")
        if listing.status != "active" or listing.available_quantity <= 0:
            raise APIError(status.HTTP_409_CONFLICT, "listing_unavailable", "A listing in your cart is no longer available.")
        if item.quantity > listing.available_quantity:
            raise APIError(
                status.HTTP_409_CONFLICT,
                "quantity_exceeds_availability",
                "A cart quantity exceeds available inventory.",
            )
        currencies.add(listing.currency.upper())
    if len(currencies) != 1:
        raise APIError(status.HTTP_409_CONFLICT, "mixed_currency_cart", "Checkout requires all cart items to use one currency.")
    return next(iter(currencies))


def summary_from_items(*, user: User, items: list[CartItem]) -> CheckoutSummary:
    currency = _validate_items(items)
    lines = [
        CheckoutItemRead(
            cart_item_id=item.id,
            listing_id=item.listing_id,
            product_id=item.listing.product_id,
            product_variant_id=item.listing.product_variant_id,
            product_name=item.listing.product.name,
            product_slug=item.listing.product.slug,
            product_image_url=item.listing.product.image_url,
            variant_label=variant_label(item.listing),
            quantity=item.quantity,
            unit_price_cents=item.listing.price_cents,
            line_total_cents=item.listing.price_cents * item.quantity,
        )
        for item in items
    ]
    subtotal = sum(line.line_total_cents for line in lines)
    return CheckoutSummary(
        items=lines,
        currency=currency,
        subtotal_cents=subtotal,
        shipping_cents=0,
        tax_cents=0,
        total_cents=subtotal,
        checkout_mode=settings.checkout_mode,
        order_placement_enabled=settings.checkout_mode == CheckoutMode.MANUAL,
        checkout_token=checkout_token_for_items(user_id=user.id, items=items, secret=settings.secret_key),
    )


def get_checkout_summary(db: Session, *, user: User) -> CheckoutSummary:
    return summary_from_items(user=user, items=_cart_items(db, user.id))


def get_locked_cart_items(db: Session, *, user: User) -> list[CartItem]:
    return _cart_items(db, user.id, lock=True)
