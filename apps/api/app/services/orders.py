from __future__ import annotations

import hmac
from datetime import datetime, timezone
from uuid import UUID

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.errors import APIError
from app.core.config import CheckoutMode, settings
from app.models import Listing, Order, OrderItem, User
from app.schemas.order import OrderCreateRequest, OrderItemRead, OrderPage, OrderRead, ShippingAddress
from app.services import checkout
from app.services.customer_lock import lock_customer_row
from app.services.order_identifiers import generate_order_number, normalized_request_hash


ORDER_LOAD_OPTIONS = (selectinload(Order.items),)


def _serialize_order(order: Order) -> OrderRead:
    return OrderRead(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        payment_status=order.payment_status,
        currency=order.currency,
        subtotal_cents=order.subtotal_cents,
        shipping_cents=order.shipping_cents,
        tax_cents=order.tax_cents,
        total_cents=order.total_cents,
        customer_name=order.customer_name,
        customer_email=order.customer_email,
        shipping=ShippingAddress(
            recipient_name=order.recipient_name,
            contact_email=order.contact_email,
            contact_phone=order.contact_phone,
            address_line1=order.address_line1,
            address_line2=order.address_line2,
            city=order.city,
            state=order.state,
            postal_code=order.postal_code,
            country=order.country,
        ),
        items=[OrderItemRead.model_validate(item) for item in order.items],
        confirmed_at=order.confirmed_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def _request_hash(payload: OrderCreateRequest) -> str:
    return normalized_request_hash(payload.model_dump(mode="json"))


def _existing_for_key(db: Session, *, user_id: UUID, idempotency_key: str) -> Order | None:
    return db.scalar(
        select(Order)
        .where(Order.user_id == user_id, Order.idempotency_key == idempotency_key)
        .options(*ORDER_LOAD_OPTIONS)
    )


def get_idempotent_replay(
    db: Session,
    *,
    user: User,
    payload: OrderCreateRequest,
    idempotency_key: str,
) -> OrderRead | None:
    """Resolve the winning row after the database uniqueness safeguard fires."""
    lock_customer_row(db, user.id)
    existing = _existing_for_key(db, user_id=user.id, idempotency_key=idempotency_key)
    if existing is None:
        return None
    if not hmac.compare_digest(existing.request_hash, _request_hash(payload)):
        raise APIError(
            status.HTTP_409_CONFLICT,
            "idempotency_key_reused",
            "This idempotency key was already used for different checkout data.",
        )
    return _serialize_order(existing)


def create_order(
    db: Session,
    *,
    user: User,
    payload: OrderCreateRequest,
    idempotency_key: str,
) -> OrderRead:
    if settings.checkout_mode != CheckoutMode.MANUAL:
        raise APIError(status.HTTP_409_CONFLICT, "checkout_disabled", "Order placement is disabled.")

    request_hash = _request_hash(payload)
    lock_customer_row(db, user.id)
    existing = _existing_for_key(db, user_id=user.id, idempotency_key=idempotency_key)
    if existing is not None:
        if not hmac.compare_digest(existing.request_hash, request_hash):
            raise APIError(
                status.HTTP_409_CONFLICT,
                "idempotency_key_reused",
                "This idempotency key was already used for different checkout data.",
            )
        return _serialize_order(existing)

    cart_items = checkout.get_locked_cart_items(db, user=user)
    listing_ids = sorted({item.listing_id for item in cart_items}, key=str)
    locked_listings = list(
        db.scalars(
            select(Listing)
            .where(Listing.id.in_(listing_ids))
            .order_by(Listing.id)
            .with_for_update()
            .options(selectinload(Listing.product), selectinload(Listing.product_variant))
            .execution_options(populate_existing=True)
        ).all()
    )
    listing_by_id = {listing.id: listing for listing in locked_listings}
    for item in cart_items:
        listing = listing_by_id.get(item.listing_id)
        if listing is None:
            raise APIError(status.HTTP_409_CONFLICT, "listing_unavailable", "A listing in your cart is no longer available.")
        item.listing = listing

    summary = checkout.summary_from_items(user=user, items=cart_items)
    if not hmac.compare_digest(summary.checkout_token, payload.checkout_token):
        raise APIError(
            status.HTTP_409_CONFLICT,
            "checkout_changed",
            "Your cart or inventory changed. Review the refreshed checkout summary.",
        )

    shipping = payload.shipping
    now = datetime.now(timezone.utc)
    order = Order(
        order_number=generate_order_number(),
        user_id=user.id,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        status="confirmed",
        payment_status="unpaid",
        currency=summary.currency,
        subtotal_cents=summary.subtotal_cents,
        shipping_cents=summary.shipping_cents,
        tax_cents=summary.tax_cents,
        total_cents=summary.total_cents,
        customer_name=user.name,
        customer_email=user.email,
        recipient_name=shipping.recipient_name,
        contact_email=shipping.contact_email,
        contact_phone=shipping.contact_phone,
        address_line1=shipping.address_line1,
        address_line2=shipping.address_line2,
        city=shipping.city,
        state=shipping.state,
        postal_code=shipping.postal_code,
        country=shipping.country,
        confirmed_at=now,
    )
    for item in cart_items:
        listing = item.listing
        variant = listing.product_variant
        order.items.append(
            OrderItem(
                listing_id=listing.id,
                product_id=listing.product_id,
                product_variant_id=listing.product_variant_id,
                product_name=listing.product.name,
                product_slug=listing.product.slug,
                product_image_url=listing.product.image_url,
                variant_label=checkout.variant_label(listing),
                variant_sku=variant.sku if variant else None,
                variant_size=variant.size if variant else None,
                variant_color=variant.color if variant else None,
                quantity=item.quantity,
                unit_price_cents=listing.price_cents,
                line_total_cents=listing.price_cents * item.quantity,
            )
        )
        listing.available_quantity -= item.quantity
        db.delete(item)
    db.add(order)
    db.flush()
    return _serialize_order(order)


def list_orders(db: Session, *, user: User, limit: int, offset: int) -> OrderPage:
    total = db.scalar(select(func.count()).select_from(Order).where(Order.user_id == user.id)) or 0
    orders = list(
        db.scalars(
            select(Order)
            .where(Order.user_id == user.id)
            .options(*ORDER_LOAD_OPTIONS)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return OrderPage(
        items=[_serialize_order(order) for order in orders],
        total=total,
        limit=limit,
        offset=offset,
    )


def get_order(db: Session, *, user: User, order_id: UUID) -> OrderRead:
    order = db.scalar(
        select(Order)
        .where(Order.id == order_id, Order.user_id == user.id)
        .options(*ORDER_LOAD_OPTIONS)
    )
    if order is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "order_not_found", "Order was not found.")
    return _serialize_order(order)
