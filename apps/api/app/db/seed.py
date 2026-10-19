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
            "trading-cards": "Sealed",
            "handbags": "One Size",
            "watches": "One Size",
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
    CategorySeed(
        name="Trading Cards",
        slug="trading-cards",
        description="Sealed trading-card boxes and premium collector sets.",
    ),
    CategorySeed(
        name="Handbags",
        slug="handbags",
        description="Designer totes, shoulder bags, and everyday carry pieces.",
    ),
    CategorySeed(
        name="Watches",
        slug="watches",
        description="Sport, automatic, and collectible watches.",
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
        image_url="https://static.nike.com/a/images/t_default/u_9ddf04c7-2a9a-4d76-add1-d15af8f0263d,c_scale,fl_relative,w_1.0,h_1.0,fl_layer_apply/350e7f3a-979a-402b-9396-a8a998dd76ab/AIR+FORCE+1+%2707.png",
        lowest_ask_cents=8700,
        total_sold=738,
    ),
    ProductSeed(
        category_slug="sneakers",
        name="Nike Dunk Low Retro White Black",
        slug="nike-dunk-low-retro-white-black",
        brand="Nike",
        description="Classic black-and-white Dunk Low with heritage basketball styling.",
        image_url="https://images.stockx.com/images/Nike-Dunk-Low-Retro-White-Black-2021-Product.jpg?fit=fill&bg=FFFFFF&w=700&h=500&auto=format,compress&q=90&dpr=2&trim=color",
        lowest_ask_cents=20900,
        total_sold=1538,
    ),
    ProductSeed(
        category_slug="sneakers",
        name="Air Jordan 4 Retro Bred",
        slug="air-jordan-4-retro-bred",
        brand="Jordan",
        description="Iconic black, cement grey, and red Air Jordan 4 colorway.",
        image_url="https://static.highsnobiety.com/thumbor/VMSpJeVhw8msloD5DDRbY07tWG8=/1600x1067/static.highsnobiety.com/wp-content/uploads/2019/03/12104430/nike-air-jordan-4-bred-release-date-price-011.jpg",
        lowest_ask_cents=22000,
        total_sold=924,
    ),
    ProductSeed(
        category_slug="sneakers",
        name="adidas Yeezy Boost 350 V2 Zebra",
        slug="adidas-yeezy-boost-350-v2-zebra",
        brand="adidas",
        description="Zebra-patterned Primeknit Yeezy Boost 350 V2 release.",
        image_url="https://images.stockx.com/images/adidas-Yeezy-Boost-350-V2-Zebra-Product.jpg?fit=fill&bg=FFFFFF&w=700&h=500&auto=format,compress&q=90&dpr=2&trim=color",
        lowest_ask_cents=31500,
        total_sold=1204,
    ),
    ProductSeed(
        category_slug="sneakers",
        name="Nike Dunk Low Retro University Blue",
        slug="nike-dunk-low-retro-university-blue",
        brand="Nike",
        description="White and University Blue edition of the Nike Dunk Low Retro.",
        image_url="https://static.nike.com/a/images/t_default/u_9ddf04c7-2a9a-4d76-add1-d15af8f0263d,c_scale,fl_relative,w_1.0,h_1.0,fl_layer_apply/361e8909-8d21-4198-a5cf-dcaf316280fb/NIKE+DUNK+LOW+RETRO.png",
        lowest_ask_cents=18000,
        total_sold=890,
    ),
    ProductSeed(
        category_slug="sneakers",
        name="Nike Air Max 90 Cool Grey Light Army",
        slug="nike-air-max-90-cool-grey-light-army",
        brand="Nike",
        description="Layered Air Max 90 with visible cushioning and a classic Waffle sole.",
        image_url="https://static.nike.com/a/images/t_default/u_9ddf04c7-2a9a-4d76-add1-d15af8f0263d,c_scale,fl_relative,w_1.0,h_1.0,fl_layer_apply/895721dd-4cfd-4219-b167-5e6d46404bc2/NIKE+AIR+MAX+90.png",
        lowest_ask_cents=13500,
        total_sold=640,
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
        category_slug="streetwear",
        name="Juice Wrld x Vlone 999 T-Shirt Black",
        slug="juice-wrld-x-vlone-999-t-shirt-black",
        brand="Vlone",
        description="Black Juice Wrld and Vlone collaboration tee with 999 graphics.",
        image_url="https://images.stockx.com/images/Juice-Wrld-x-Vlone-999-T-Shirt-Black.png?fit=fill&bg=FFFFFF&w=700&h=500&auto=compress&trim=color&q=90&dpr=1&updated_at=1608068134&fm=webp",
        lowest_ask_cents=5900,
        total_sold=361,
    ),
    ProductSeed(
        category_slug="streetwear",
        name="Supreme Tiffany & Co. Box Logo Tee White",
        slug="supreme-tiffany-and-co-box-logo-tee-white",
        brand="Supreme",
        description="White Supreme box logo tee from the Tiffany & Co. collaboration.",
        image_url="https://images.stockx.com/images/Supreme-Tiffany-Co-Box-Logo-Tee-White.jpg?fit=fill&bg=FFFFFF&w=700&h=500&auto=compress&trim=color&q=90&dpr=1&updated_at=1636647311&fm=webp",
        lowest_ask_cents=28400,
        total_sold=175,
    ),
    ProductSeed(
        category_slug="streetwear",
        name="Pop Smoke x Vlone The Woo T-Shirt Black",
        slug="pop-smoke-x-vlone-the-woo-t-shirt-black",
        brand="Vlone",
        description="Black Pop Smoke and Vlone collaboration tee from The Woo collection.",
        image_url="https://images.stockx.com/images/Pop-Smoke-x-Vlone-The-Woo-T-Shirt-Black.png?fit=fill&bg=FFFFFF&w=700&h=500&auto=compress&trim=color&q=90&dpr=1&updated_at=1606318864&fm=webp",
        lowest_ask_cents=5900,
        total_sold=161,
    ),
    ProductSeed(
        category_slug="streetwear",
        name="Travis Scott Cactus Jack + KAWS for Fragment Tee Grey",
        slug="travis-scott-cactus-jack-kaws-fragment-tee-grey",
        brand="Cactus Jack",
        description="Grey collaboration tee from Cactus Jack, KAWS, and Fragment.",
        image_url="https://images.stockx.com/images/Travis-Scott-Cactus-Jack-Kaws-For-Fragment-Tee-Grey.jpg?fit=fill&bg=FFFFFF&w=140&h=75&auto=compress&trim=color&q=90&dpr=1&updated_at=1627941057&fm=webp",
        lowest_ask_cents=4700,
        total_sold=131,
    ),
    ProductSeed(
        category_slug="streetwear",
        name="Juice Wrld x XO x Vlone Double Agent Tee Natural",
        slug="juice-wrld-x-xo-x-vlone-double-agent-tee-natural",
        brand="Vlone",
        description="Natural-color Double Agent tee from Juice Wrld, XO, and Vlone.",
        image_url="https://images.stockx.com/images/Juice-Wrld-x-XO-x-Vlone-Double-Agent-Tee-Natural.png?fit=fill&bg=FFFFFF&w=140&h=75&auto=compress&trim=color&q=90&dpr=1&updated_at=1611842418&fm=webp",
        lowest_ask_cents=5500,
        total_sold=120,
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
    ProductSeed(
        category_slug="collectibles",
        name="LEGO Botanical Collection Bonsai Tree Set 10281",
        slug="lego-botanical-collection-bonsai-tree-set-10281",
        brand="LEGO",
        description="Display-ready LEGO Botanical Collection bonsai tree building set.",
        image_url="https://images.stockx.com/images/Lego-Bonsai-Tree-Set-10281.jpg?fit=fill&bg=FFFFFF&w=700&h=500&auto=compress&trim=color&q=90&dpr=1&updated_at=1611070347&fm=webp",
        lowest_ask_cents=5700,
        total_sold=0,
    ),
    ProductSeed(
        category_slug="collectibles",
        name="LEGO Botanical Collection Flower Bouquet Set 10280",
        slug="lego-botanical-collection-flower-bouquet-set-10280",
        brand="LEGO",
        description="Buildable flower bouquet from the LEGO Botanical Collection.",
        image_url="https://images.stockx.com/images/Lego-Flower-Bouqet-Set-10280.png?fit=fill&bg=FFFFFF&w=700&h=500&auto=compress&trim=color&q=90&dpr=1&updated_at=1611070374&fm=webp",
        lowest_ask_cents=6000,
        total_sold=0,
    ),
    ProductSeed(
        category_slug="collectibles",
        name="LEGO Santa's Visit Winter Village Set 10293",
        slug="lego-santas-visit-winter-village-set-10293",
        brand="LEGO",
        description="Holiday-themed Winter Village display set featuring Santa's visit.",
        image_url="https://images.stockx.com/images/LEGO-Santas-Visit-Winter-Village-Set-10293.jpg?fit=fill&bg=FFFFFF&w=700&h=500&auto=compress&trim=color&q=90&dpr=1&updated_at=1631216841&fm=webp",
        lowest_ask_cents=17800,
        total_sold=0,
    ),
    ProductSeed(
        category_slug="collectibles",
        name="LEGO Titanic Set 10294",
        slug="lego-titanic-set-10294",
        brand="LEGO",
        description="Large-scale display model of the RMS Titanic with detailed sections.",
        image_url="https://images.stockx.com/images/LEGO-Titanic-Set-10294.jpg?fit=fill&bg=FFFFFF&w=700&h=500&auto=compress&trim=color&q=90&dpr=1&updated_at=1634243427&fm=webp",
        lowest_ask_cents=79700,
        total_sold=0,
    ),
    ProductSeed(
        category_slug="collectibles",
        name='MSCHF Boosted Packs V3 "Mariah Carey Edition" Individual Pack',
        slug="mschf-boosted-packs-v3-mariah-carey-edition-individual-pack",
        brand="MSCHF",
        description="Sealed individual novelty trading-card pack from MSCHF's third Boosted Packs release.",
        image_url="https://images.stockx.com/images/MSCHF-Boosted-Packs-V3-Mariah-Carey-Edition-Individual-Pack.png?fit=fill&bg=FFFFFF&w=700&h=500&auto=compress&trim=color&q=90&dpr=1&updated_at=1638382773&fm=webp",
        lowest_ask_cents=13900,
        total_sold=0,
    ),
    ProductSeed(
        category_slug="trading-cards",
        name="Pokemon TCG Scarlet & Violet Paldea Evolved Booster Box",
        slug="pokemon-tcg-scarlet-violet-paldea-evolved-booster-box",
        brand="Pokemon",
        description="Factory-sealed Paldea Evolved booster display containing 36 packs.",
        image_url="https://forevertcg.com/cdn/shop/files/s-l1200.webp?v=1712049462&width=1946",
        lowest_ask_cents=13500,
        total_sold=320,
    ),
    ProductSeed(
        category_slug="trading-cards",
        name="Pokemon TCG Scarlet & Violet Journey Together Booster Box",
        slug="pokemon-tcg-scarlet-violet-journey-together-booster-box",
        brand="Pokemon",
        description="Sealed Journey Together booster box with 36 trading-card packs.",
        image_url="https://cdn.shopify.com/s/files/1/0817/1297/2120/files/Pokemon_Journey_Together_Booster_Box.png?v=1767965841&width=1920",
        lowest_ask_cents=14500,
        total_sold=248,
    ),
    ProductSeed(
        category_slug="trading-cards",
        name="Pokemon TCG Scarlet & Violet Surging Sparks Booster Box",
        slug="pokemon-tcg-scarlet-violet-surging-sparks-booster-box",
        brand="Pokemon",
        description="Sealed Surging Sparks booster display featuring 36 packs.",
        image_url="https://dacardworld1.imgix.net/857836_005_110524.jpg?auto=format%2Ccompress&fm=jpg&h=1800&ixlib=php-3.3.1&s=2f8a9b595a213c04e0afc8bc9929a279&w=1800",
        lowest_ask_cents=19000,
        total_sold=275,
    ),
    ProductSeed(
        category_slug="trading-cards",
        name="Pokemon TCG Sword & Shield Astral Radiance Booster Box",
        slug="pokemon-tcg-sword-shield-astral-radiance-booster-box",
        brand="Pokemon",
        description="Factory-sealed Astral Radiance booster box containing 36 packs.",
        image_url="https://www.vortexstore.eu/cdn/shop/files/133_pokemon-astral-radiance-booster-box-36-doplnkovych-boosteru.webp?v=1737633874&width=1024",
        lowest_ask_cents=18000,
        total_sold=194,
    ),
    ProductSeed(
        category_slug="trading-cards",
        name="Pokemon TCG Scarlet & Violet 151 Ultra-Premium Collection",
        slug="pokemon-tcg-scarlet-violet-151-ultra-premium-collection",
        brand="Pokemon",
        description="Premium Mew-themed collection with booster packs, promos, and accessories.",
        image_url="https://www.hobby-addicts.com/cdn/shop/files/Pokemon_TCG_Scarlet_Violet_151_Ultra-Premium_Collection.png?v=1686972224&width=3786",
        lowest_ask_cents=23000,
        total_sold=412,
    ),
    ProductSeed(
        category_slug="handbags",
        name="Telfar Small Shopping Bag Black",
        slug="telfar-small-shopping-bag-black",
        brand="Telfar",
        description="Compact black shopping bag with dual handles and a crossbody strap.",
        image_url="https://images.stockx.com/images/Telfar-Shopping-Bag-Small-Black-Product.jpg?fit=fill&bg=FFFFFF&w=700&h=500&auto=format,compress&q=90&dpr=2&trim=color",
        lowest_ask_cents=18000,
        total_sold=540,
    ),
    ProductSeed(
        category_slug="handbags",
        name="Coach Tabby Shoulder Bag 26 Black",
        slug="coach-tabby-shoulder-bag-26-black",
        brand="Coach",
        description="Black pebble-leather shoulder bag with signature gold C hardware.",
        image_url="https://s7d2.scene7.com/is/image/Coach/ch857_b4bk_a0?fmt=jpeg&hei=1800&wid=1800",
        lowest_ask_cents=45000,
        total_sold=286,
    ),
    ProductSeed(
        category_slug="handbags",
        name="Marc Jacobs The Canvas Large Tote Bag Black",
        slug="marc-jacobs-canvas-large-tote-bag-black",
        brand="Marc Jacobs",
        description="Large black cotton-canvas tote with bold signature lettering.",
        image_url="https://www.nk.se/globalassets/60918315_51144210_1.png",
        lowest_ask_cents=22000,
        total_sold=371,
    ),
    ProductSeed(
        category_slug="handbags",
        name="Longchamp Le Pliage Original Medium Tote Black",
        slug="longchamp-le-pliage-original-medium-tote-black",
        brand="Longchamp",
        description="Foldable black recycled-canvas tote with brown leather trim.",
        image_url="https://cdn-longchamp.sm.mncdn.com/content/images/684bfe535a7ac29dbd468f12_0.png",
        lowest_ask_cents=14000,
        total_sold=462,
    ),
    ProductSeed(
        category_slug="handbags",
        name="Christian Dior Large Cannage Lady Dior Bag Pink",
        slug="christian-dior-large-cannage-lady-dior-bag-pink",
        brand="Christian Dior",
        description="Large pink Cannage leather Lady Dior bag with gold-tone hardware.",
        image_url="https://www.oliverjewellery.ca/cdn/shop/files/Christian-Dior-Pink-Large-Cannage-Lady-Dior-Bag-w-Strap-Authenticity-Card-5.jpg?v=1685164196",
        lowest_ask_cents=520000,
        total_sold=68,
    ),
    ProductSeed(
        category_slug="watches",
        name="Tissot PRX Powermatic 80 Blue 40mm",
        slug="tissot-prx-powermatic-80-blue-40mm",
        brand="Tissot",
        description="Swiss automatic steel watch with a blue waffle dial and 80-hour power reserve.",
        image_url="https://www.tissotwatches.com/dw/image/v2/BKKD_PRD/on/demandware.static/-/Sites-Tissot-Catalogue/default/dw95c4331d/product-pictures/63f42767-a9f5-4cdd-b952-8ea7b82b7e0c_T137-407-11-041-00_shadow.png?sh=1200&sm=cut&sw=1200",
        lowest_ask_cents=85000,
        total_sold=338,
    ),
    ProductSeed(
        category_slug="watches",
        name="Casio G-Shock GA-2100-1A1 All Black",
        slug="casio-g-shock-ga-2100-1a1-all-black",
        brand="Casio",
        description="Slim all-black analog-digital G-Shock with a carbon-core case.",
        image_url="https://www.casio.com/content/dam/casio/product-info/locales/uk/en-gb/timepiece/product/watch/G/GA/GA2/GA-2100-1A1/assets/GA-2100-1A1_Seq01.png.transform/product-panel/image.png",
        lowest_ask_cents=9900,
        total_sold=782,
    ),
    ProductSeed(
        category_slug="watches",
        name="Seiko 5 Sports SRPD55 Automatic Black",
        slug="seiko-5-sports-srpd55-automatic-black",
        brand="Seiko",
        description="Automatic steel sports watch with a black dial, rotating bezel, and day-date display.",
        image_url="https://seikousa.com/cdn/shop/products/SRPD55_1_002a37a5-1afe-4af9-bbeb-5df30d044800.png?v=1744226991&width=713",
        lowest_ask_cents=35000,
        total_sold=426,
    ),
    ProductSeed(
        category_slug="watches",
        name="Citizen Tsuyosa NJ0150-81L Automatic Blue",
        slug="citizen-tsuyosa-nj0150-81l-automatic-blue",
        brand="Citizen",
        description="Stainless-steel automatic watch with a blue sunburst dial and integrated bracelet.",
        image_url="https://media.citizen.it/ImgOriginal/citizen_NJ0150-81L_01_2000x2000.jpg",
        lowest_ask_cents=45000,
        total_sold=294,
    ),
    ProductSeed(
        category_slug="watches",
        name="Omega x Swatch MoonSwatch Mission to the Moon",
        slug="omega-x-swatch-moonswatch-mission-to-the-moon",
        brand="Swatch",
        description="Bioceramic lunar-inspired chronograph based on the Omega Speedmaster design.",
        image_url="https://balazskicks.com/cdn/shop/files/19_952db081-0830-42e2-b9af-f240f48d4282.png?v=1732270513&width=1500",
        lowest_ask_cents=27000,
        total_sold=615,
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
