from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("lowest_ask_cents IS NULL OR lowest_ask_cents >= 0", name="lowest_ask_cents_non_negative"),
        CheckConstraint("total_sold >= 0", name="total_sold_non_negative"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    lowest_ask_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_sold: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    category = relationship("Category", back_populates="products")
    variants = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    listings = relationship("Listing", back_populates="product", cascade="all, delete-orphan")
    watchlist_items = relationship("WatchlistItem", back_populates="product", cascade="all, delete-orphan")


class ProductVariant(TimestampMixin, Base):
    __tablename__ = "product_variants"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    size: Mapped[str | None] = mapped_column(String(64), nullable=True)
    color: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sku: Mapped[str | None] = mapped_column(String(128), nullable=True)

    product = relationship("Product", back_populates="variants")
    listings = relationship("Listing", back_populates="product_variant")

