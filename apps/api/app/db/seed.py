from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Category, Product


@dataclass(frozen=True)
class CategorySeed:
    name: str
    slug: str
    description: str


@dataclass(frozen=True)
class ProductSeed:
    category_slug: str
    name: str
    slug: str
    brand: str | None
    description: str | None
    image_url: str | None
    lowest_ask_cents: int | None
    total_sold: int


CATEGORIES = [
    CategorySeed(
        name="Sneakers",
        slug="sneakers",
        description="Marketplace sneaker releases and popular shoes.",
    ),
    CategorySeed(
        name="Streetwear",
        slug="streetwear",
        description="Apparel, hoodies, tees, and accessories.",
    ),
    CategorySeed(
        name="Collectibles",
        slug="collectibles",
        description="Trading cards, figures, consoles, and collectible goods.",
    ),
]

PRODUCTS = [
    ProductSeed(
        category_slug="sneakers",
        name="Jordan 1 Retro High Element Gore-Tex Black Particle Grey",
        slug="jordan-1-retro-high-element-gore-tex-black-particle-grey",
        brand="Jordan",
        description="Representative sneaker release from the static storefront.",
        image_url="https://images.stockx.com/images/Air-Jordan-1-Retro-High-Element-Gore-Tex-Black-Particle-Grey.jpg?fit=fill&bg=FFFFFF&w=480&h=320&auto=compress&q=90&dpr=1",
        lowest_ask_cents=24300,
        total_sold=0,
    ),
    ProductSeed(
        category_slug="sneakers",
        name="Nike Dunk Low Pink Velvet GS",
        slug="nike-dunk-low-pink-velvet-gs",
        brand="Nike",
        description="Representative Nike Dunk product from the static storefront.",
        image_url="https://images.stockx.com/360/Nike-Dunk-Low-Pink-Velvet-GS/Images/Nike-Dunk-Low-Pink-Velvet-GS/Lv2/img01.jpg?auto=compress&w=480&q=90&dpr=1&h=320&fm=webp",
        lowest_ask_cents=32200,
        total_sold=0,
    ),
    ProductSeed(
        category_slug="streetwear",
        name="Supreme Box Logo Hooded Sweatshirt Black",
        slug="supreme-box-logo-hooded-sweatshirt-black",
        brand="Supreme",
        description="Representative hoodie from the static streetwear page.",
        image_url="https://images.stockx.com/images/Supreme-Box-Logo-Hooded-Sweatshirt-FW21-Black.png?fit=fill&bg=FFFFFF&w=140&h=75&auto=compress&trim=color&q=90&dpr=1&fm=webp",
        lowest_ask_cents=5700,
        total_sold=437,
    ),
    ProductSeed(
        category_slug="streetwear",
        name="Off-White x Jordan T-shirt Black",
        slug="off-white-x-jordan-t-shirt-black",
        brand="Off-White",
        description="Representative T-shirt from the static streetwear page.",
        image_url="https://images.stockx.com/images/Off-White-x-Jordan-T-shirt-Black.png?fit=fill&bg=FFFFFF&w=140&h=75&auto=compress&trim=color&q=90&dpr=1&fm=webp",
        lowest_ask_cents=12200,
        total_sold=291,
    ),
    ProductSeed(
        category_slug="collectibles",
        name="Pokemon TCG 25th Anniversary Celebrations Ultra-Premium Collection Box",
        slug="pokemon-tcg-25th-anniversary-celebrations-ultra-premium-collection-box",
        brand="Pokemon",
        description="Representative trading-card product from the static storefront.",
        image_url="https://images.stockx.com/images/Pokemon-TCG-25th-Anniversary-Celebrations-Ultra-Premium-Collection-Box.jpg?fit=fill&bg=FFFFFF&w=700&h=500&auto=format,compress&q=90&dpr=2&trim=color",
        lowest_ask_cents=27000,
        total_sold=0,
    ),
    ProductSeed(
        category_slug="collectibles",
        name="Bearbrick x Transformers Optimus Prime x BAPE 200% Black",
        slug="bearbrick-x-transformers-optimus-prime-x-bape-200-black",
        brand="Bearbrick",
        description="Representative figure from the static storefront.",
        image_url="https://images.stockx.com/images/Bearbrick-x-Transformers-Optimus-Prime-x-BAPE-200-Black.jpg?fit=fill&bg=FFFFFF&w=480&h=320&auto=compress&q=90&dpr=1&trim=color&fm=webp",
        lowest_ask_cents=11700,
        total_sold=0,
    ),
]


def upsert_categories(session: Session) -> None:
    for category in CATEGORIES:
        statement = insert(Category).values(
            name=category.name,
            slug=category.slug,
            description=category.description,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[Category.slug],
            set_={
                "name": statement.excluded.name,
                "description": statement.excluded.description,
            },
        )
        session.execute(statement)


def upsert_products(session: Session) -> None:
    categories = {
        category.slug: category.id
        for category in session.scalars(select(Category)).all()
    }

    for product in PRODUCTS:
        statement = insert(Product).values(
            category_id=categories[product.category_slug],
            name=product.name,
            slug=product.slug,
            brand=product.brand,
            description=product.description,
            image_url=product.image_url,
            lowest_ask_cents=product.lowest_ask_cents,
            total_sold=product.total_sold,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[Product.slug],
            set_={
                "category_id": statement.excluded.category_id,
                "name": statement.excluded.name,
                "brand": statement.excluded.brand,
                "description": statement.excluded.description,
                "image_url": statement.excluded.image_url,
                "lowest_ask_cents": statement.excluded.lowest_ask_cents,
                "total_sold": statement.excluded.total_sold,
            },
        )
        session.execute(statement)


def seed_database() -> None:
    from app.db.session import SessionLocal

    with SessionLocal() as session:
        upsert_categories(session)
        upsert_products(session)
        session.commit()


if __name__ == "__main__":
    seed_database()
    print("Seeded categories and products.")
