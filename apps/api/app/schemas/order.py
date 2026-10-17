from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator

from app.core.config import CheckoutMode


def _strip_text(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(str(value).strip().split())


class OrderStatus(StrEnum):
    PENDING_PAYMENT = "pending_payment"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class PaymentStatus(StrEnum):
    UNPAID = "unpaid"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentAttemptStatus(StrEnum):
    INITIALIZING = "initializing"
    OPEN = "open"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ShippingAddress(BaseModel):
    recipient_name: str = Field(min_length=1, max_length=255)
    contact_email: str = Field(min_length=3, max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    contact_phone: str = Field(min_length=7, max_length=32, pattern=r"^[0-9+().\-\s]+$")
    address_line1: str = Field(min_length=1, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=120)
    state: str | None = Field(default=None, max_length=120)
    postal_code: str = Field(min_length=1, max_length=32)
    country: str = Field(min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")

    @field_validator(
        "recipient_name",
        "contact_email",
        "contact_phone",
        "address_line1",
        "address_line2",
        "city",
        "state",
        "postal_code",
        mode="before",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return _strip_text(value)

    @field_validator("contact_email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.casefold()

    @field_validator("country")
    @classmethod
    def normalize_country(cls, value: str) -> str:
        return value.upper()


class CheckoutItemRead(BaseModel):
    cart_item_id: UUID
    listing_id: UUID
    product_id: UUID
    product_variant_id: UUID | None = None
    product_name: str
    product_slug: str
    product_image_url: str | None = None
    variant_label: str | None = None
    quantity: int = Field(gt=0)
    unit_price_cents: int = Field(ge=0)
    line_total_cents: int = Field(ge=0)


class CheckoutSummary(BaseModel):
    items: list[CheckoutItemRead]
    currency: str = Field(min_length=3, max_length=3)
    subtotal_cents: int = Field(ge=0)
    shipping_cents: int = Field(ge=0)
    tax_cents: int = Field(ge=0)
    total_cents: int = Field(ge=0)
    checkout_mode: CheckoutMode
    order_placement_enabled: bool
    checkout_token: str


class OrderCreateRequest(BaseModel):
    checkout_token: str = Field(min_length=1, max_length=255)
    shipping: ShippingAddress

    model_config = ConfigDict(extra="forbid")


class PaymentSessionCreateRequest(OrderCreateRequest):
    pass


class PaymentAttemptSummary(BaseModel):
    id: UUID
    provider: Literal["stripe"]
    status: PaymentAttemptStatus
    amount_cents: int = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    expires_at: datetime
    completed_at: datetime | None = None
    failure_code: str | None = Field(default=None, min_length=1, max_length=100, pattern=r"^[a-z0-9_]+$")

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class PaymentSessionRead(BaseModel):
    order_id: UUID
    payment_attempt_id: UUID
    provider_session_id: str = Field(min_length=8, max_length=255, pattern=r"^cs_(?:test|live)_[A-Za-z0-9_]+$")
    status: PaymentAttemptStatus
    url: AnyHttpUrl | None
    expires_at: datetime

    @field_validator("url")
    @classmethod
    def require_stripe_hosted_url(cls, value: AnyHttpUrl | None) -> AnyHttpUrl | None:
        if value is None:
            return None
        parsed = urlsplit(str(value))
        if parsed.scheme != "https" or parsed.hostname != "checkout.stripe.com":
            raise ValueError("payment session URL must be hosted by checkout.stripe.com")
        return value

    model_config = ConfigDict(extra="forbid")


class PaymentCancellationRead(BaseModel):
    order_id: UUID
    order_status: OrderStatus
    payment_status: PaymentStatus
    attempt_status: PaymentAttemptStatus
    inventory_released_at: datetime | None = None

    model_config = ConfigDict(extra="forbid")


class OrderItemRead(BaseModel):
    id: UUID
    listing_id: UUID | None = None
    product_id: UUID | None = None
    product_variant_id: UUID | None = None
    product_name: str
    product_slug: str
    product_image_url: str | None = None
    variant_label: str | None = None
    variant_sku: str | None = None
    variant_size: str | None = None
    variant_color: str | None = None
    quantity: int
    unit_price_cents: int
    line_total_cents: int

    model_config = ConfigDict(from_attributes=True)


class OrderRead(BaseModel):
    id: UUID
    order_number: str
    status: OrderStatus
    payment_status: PaymentStatus
    currency: str
    subtotal_cents: int
    shipping_cents: int
    tax_cents: int
    total_cents: int
    customer_name: str
    customer_email: str
    shipping: ShippingAddress
    items: list[OrderItemRead]
    reservation_expires_at: datetime | None = None
    inventory_released_at: datetime | None = None
    payment_attempts: list[PaymentAttemptSummary] = Field(default_factory=list)
    confirmed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class OrderPage(BaseModel):
    items: list[OrderRead]
    total: int
    limit: int
    offset: int
