from __future__ import annotations

from fastapi import status
from sqlalchemy.orm import Session

from app.api.errors import APIError
from app.models import Listing, Product, ProductVariant, User


def create_listing(
    db: Session,
    *,
    user: User,
    product_id,
    product_variant_id,
    price_cents: int,
    currency: str,
) -> Listing:
    product = db.get(Product, product_id)
    if product is None:
        raise APIError(status.HTTP_404_NOT_FOUND, "product_not_found", "Product was not found.")

    if product_variant_id is not None:
        variant = db.get(ProductVariant, product_variant_id)
        if variant is None or variant.product_id != product.id:
            raise APIError(status.HTTP_404_NOT_FOUND, "variant_not_found", "Product variant was not found.")

    listing = Listing(
        user_id=user.id,
        product_id=product.id,
        product_variant_id=product_variant_id,
        price_cents=price_cents,
        currency=currency.upper(),
        status="active",
    )
    db.add(listing)
    db.flush()
    return listing

