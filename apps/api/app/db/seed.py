from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from dataclasses import dataclass
import sys

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Category, Listing, Product, ProductVariant, User
from app.services.auth import normalize_email


SEED_INVENTORY_QUANTITY = 10
SEED_SKU_PREFIX = "SEED-"


class SeedInventoryOwnerError(ValueError):
    """Raised when inventory seeding cannot use the requested owner."""


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

    @property
    def seed_size(self) -> str:
        return {
            "sneakers": "10",
            "streetwear": "M",
            "collectibles": "One Size",
        }[self.category_slug]

    @property
    def seed_sku(self) -> str:
        return f"{SEED_SKU_PREFIX}{self.slug.upper()}"


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
        image_url="https://images.stockx.com/images/Air-Jordan-1-Retro-High-Element-Gore-Tex-Product.jpg?bg=FFFFFF&dpr=1&fit=fill&h=857&q=60&trim=color&updated_at=1738193358&w=1200",
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
        category_slug="sneakers",
        name="New Balance 1300 Aimé Leon Dore Green",
        slug="new-balance-1300-aime-leon-dore-green",
        brand="New Balance",
        description="Representative New Balance collaboration from the static storefront.",
        image_url="https://images.stockx.com/images/New-Balance-1300-Aime-Leon-Dore-Green-Product.jpg?fit=fill&bg=FFFFFF&w=700&h=500&auto=format,compress&q=90&dpr=2&trim=color&updated_at=1616604407",
        lowest_ask_cents=17400,
        total_sold=515,
    ),
    ProductSeed(
        category_slug="sneakers",
        name="Air Jordan 1 UNC to Chicago",
        slug="air-jordan-1-unc-to-chicago",
        brand="Jordan",
        description="Representative Air Jordan 1 colorway from the static storefront.",
        image_url="https://static.highsnobiety.com/thumbor/ebEN_AO6_84VUp8E6HV2aaXxlts=/1600x1067/static.highsnobiety.com/wp-content/uploads/2019/10/04174350/air-jordan-1-unc-to-chicago-release-date-price-1-02.jpg",
        lowest_ask_cents=17000,
        total_sold=2388,
    ),
    ProductSeed(
        category_slug="sneakers",
        name="Nike Air Force 1 Low White",
        slug="nike-air-force-1-low-white",
        brand="Nike",
        description="Representative Nike Air Force 1 from the static storefront.",
        image_url="https://images.stockx.com/images/Nike-Air-Force-1-Low-White-07_V2-Product.jpg?fit=fill&bg=FFFFFF&w=700&h=500&auto=format,compress&q=90&dpr=2&trim=color&updated_at=1631122839",
        lowest_ask_cents=8700,
        total_sold=738,
    ),
    ProductSeed(
        category_slug="streetwear",
        name="Supreme Box Logo Hooded Sweatshirt Black",
        slug="supreme-box-logo-hooded-sweatshirt-black",
        brand="Supreme",
        description="Representative hoodie from the static streetwear page.",
        image_url="https://images.stockx.com/images/Supreme-Box-Logo-Hooded-Sweatshirt-FW21-Black.jpg?bg=FFFFFF&dpr=3&fit=fill&h=384&q=41&trim=color&updated_at=1639059555&w=576",
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
        category_slug="streetwear",
        name="Juice Wrld x Vlone Butterfly T-Shirt White",
        slug="juice-wrld-x-vlone-butterfly-t-shirt-white",
        brand="Vlone",
        description="Representative graphic T-shirt from the static streetwear page.",
        image_url="https://images.stockx.com/images/Juice-Wrld-x-Vlone-Butterfly-T-Shirt-White-Product.jpg?bg=FFFFFF&dpr=2&fit=fill&h=500&q=90&trim=color&w=700",
        lowest_ask_cents=5700,
        total_sold=437,
    ),
    ProductSeed(
        category_slug="streetwear",
        name="Off-White x Jordan T-shirt White",
        slug="off-white-x-jordan-t-shirt-white",
        brand="Off-White",
        description="Representative collaboration T-shirt from the static streetwear page.",
        image_url="https://images.stockx.com/images/Off-White-x-Jordan-T-shirt-Sail.png?fit=fill&bg=FFFFFF&w=140&h=75&auto=compress&trim=color&q=90&dpr=1&updated_at=1636622355&fm=webp",
        lowest_ask_cents=11200,
        total_sold=287,
    ),
    ProductSeed(
        category_slug="streetwear",
        name="Yeezy x Gap Hoodie Black",
        slug="yeezy-x-gap-hoodie-black",
        brand="Yeezy Gap",
        description="Representative hoodie from the static streetwear page.",
        image_url="https://images.stockx.com/images/Yeezy-Gap-Logo-Hoodie-Black-Product.jpg?auto=compress&bg=FFFFFF&dpr=2&fit=fill&fm=webp&h=500&q=90&trim=color&updated_at=1746560704&w=700",
        lowest_ask_cents=10000,
        total_sold=251,
    ),
    ProductSeed(
        category_slug="collectibles",
        name="Pokemon TCG 25th Anniversary Celebrations Ultra-Premium Collection Box",
        slug="pokemon-tcg-25th-anniversary-celebrations-ultra-premium-collection-box",
        brand="Pokemon",
        description="Representative trading-card product from the static storefront.",
        image_url="https://papajoeys.com/cdn/shop/files/655608bd-d514-43a9-adb5-054fe4f312b5.png?v=1764807642&width=1445",
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
    ProductSeed(
        category_slug="collectibles",
        name="Microsoft Xbox Series X Mini Fridge (US Plug)",
        slug="microsoft-xbox-series-x-mini-fridge-us-plug",
        brand="Microsoft",
        description="Representative gaming collectible from the static collectibles page.",
        image_url="https://images.stockx.com/images/Microsoft-Xbox-Series-X-Mini-Fridge-AUS-Plug.jpg?auto=compress&bg=FFFFFF&dpr=2&fit=fill&fm=webp&h=857&q=60&trim=color&updated_at=1663706723&w=1200",
        lowest_ask_cents=14200,
        total_sold=0,
    ),
    ProductSeed(
        category_slug="collectibles",
        name="Virgil Abloh x Nike ICONS The Ten Book",
        slug="virgil-abloh-x-nike-icons-the-ten-book",
        brand="Nike",
        description="Representative design book from the static collectibles page.",
        image_url="https://images.stockx.com/images/Virgil-Abloh-x-Nike-The-Ten-Book-1.png?fit=fill&bg=FFFFFF&w=140&h=75&auto=compress&trim=color&q=90&dpr=1&updated_at=1610754641&fm=webp",
        lowest_ask_cents=7000,
        total_sold=0,
    ),
    ProductSeed(
        category_slug="collectibles",
        name="LEGO Ideas Home Alone Set 21330",
        slug="lego-ideas-home-alone-set-21330",
        brand="LEGO",
        description="Representative building set from the static collectibles page.",
        image_url="https://images.stockx.com/images/LEGO-Ideas-Home-Alone-Set-21330.jpg?fit=fill&bg=FFFFFF&w=140&h=75&auto=compress&trim=color&q=90&dpr=1&updated_at=1634850638&fm=webp",
        lowest_ask_cents=35000,
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


def _require_inventory_owner(session: Session, email: str) -> User:
    normalized_email = normalize_email(email)
    owner = session.scalar(select(User).where(User.email == normalized_email))
    if owner is None:
        raise SeedInventoryOwnerError(f"Inventory owner was not found: {normalized_email}")
    if not owner.is_admin:
        raise SeedInventoryOwnerError(f"Inventory owner must be an admin: {normalized_email}")
    return owner


def upsert_seed_inventory(session: Session, *, owner_email: str) -> None:
    owner = _require_inventory_owner(session, owner_email)
    products = {
        product.slug: product
        for product in session.scalars(select(Product).where(Product.slug.in_([seed.slug for seed in PRODUCTS]))).all()
    }

    for seed in PRODUCTS:
        product = products[seed.slug]
        variant = session.scalar(
            select(ProductVariant).where(
                ProductVariant.product_id == product.id,
                ProductVariant.sku == seed.seed_sku,
            )
        )
        if variant is None:
            variant = ProductVariant(product_id=product.id, size=seed.seed_size, color=None, sku=seed.seed_sku)
            session.add(variant)
            session.flush()
        else:
            variant.size = seed.seed_size
            variant.color = None

        listing = session.scalars(
            select(Listing)
            .where(
                Listing.user_id == owner.id,
                Listing.product_id == product.id,
                Listing.product_variant_id == variant.id,
            )
            .order_by(Listing.created_at, Listing.id)
        ).first()
        if listing is None:
            listing = Listing(user_id=owner.id, product_id=product.id, product_variant_id=variant.id)
            session.add(listing)
        listing.price_cents = seed.lowest_ask_cents
        listing.available_quantity = SEED_INVENTORY_QUANTITY
        listing.currency = "USD"
        listing.status = "active"


def seed_database(
    *,
    inventory_owner_email: str | None = None,
    session_factory: Callable[[], Session] | None = None,
) -> None:
    if session_factory is None:
        from app.db.session import SessionLocal

        session_factory = SessionLocal

    with session_factory() as session:
        upsert_categories(session)
        upsert_products(session)
        if inventory_owner_email is not None:
            upsert_seed_inventory(session, owner_email=inventory_owner_email)
        session.commit()


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed the StockX development catalog and optional inventory.")
    parser.add_argument(
        "--inventory-owner-email",
        help="Existing admin email that will own deterministic seeded inventory.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        seed_database(inventory_owner_email=args.inventory_owner_email)
    except SeedInventoryOwnerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.inventory_owner_email:
        print(f"Seeded categories, products, and inventory for {normalize_email(args.inventory_owner_email)}.")
    else:
        print("Seeded categories and products.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
