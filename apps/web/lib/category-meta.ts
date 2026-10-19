export type CategoryMeta = {
  slug: string;
  label: string;
  description: string;
  imageUrl: string;
  filters: string[];
};

const meta: Record<string, CategoryMeta> = {
  sneakers: {
    slug: "sneakers",
    label: "Sneakers",
    description: "Marketplace sneaker releases, popular shoes, and everyday grails.",
    imageUrl:
      "https://images.stockx.com/images/Air-Jordan-1-Retro-High-Element-Gore-Tex-Black-Particle-Grey.jpg?fit=fill&bg=FFFFFF&w=960&h=420&auto=compress&q=90&dpr=1",
    filters: ["Jordan", "Nike", "Adidas", "New Balance", "Dunks", "Yeezy"]
  },
  streetwear: {
    slug: "streetwear",
    label: "Streetwear",
    description: "Apparel, hoodies, tees, accessories, and culture-defining drops.",
    imageUrl: "https://stockx-assets.imgix.net/Core/browse-header-streetwear.jpg?auto=compress,format",
    filters: ["Supreme", "BAPE", "Nike", "Off-White", "Essentials", "Fear of God", "KAWS"]
  },
  collectibles: {
    slug: "collectibles",
    label: "Collectibles",
    description: "Trading cards, figures, toys, consoles, and collector goods.",
    imageUrl: "https://stockx-assets.imgix.net/Core/browse-header-collectibles.jpg?auto=compress,format",
    filters: ["Pokemon", "Bearbrick", "LEGO", "Funko Pop", "Art Prints", "Action Figures"]
  },
  "trading-cards": {
    slug: "trading-cards",
    label: "Trading Cards",
    description: "Sealed booster boxes and premium collector sets from sought-after releases.",
    imageUrl:
      "https://www.hobby-addicts.com/cdn/shop/files/Pokemon_TCG_Scarlet_Violet_151_Ultra-Premium_Collection.png?v=1686972224&width=3786",
    filters: ["Pokemon", "Scarlet & Violet", "Sword & Shield", "Booster Boxes", "Premium Collections"]
  },
  handbags: {
    slug: "handbags",
    label: "Handbags",
    description: "Designer totes, shoulder bags, and statement pieces for everyday carry.",
    imageUrl:
      "https://s7d2.scene7.com/is/image/Coach/ch857_b4bk_a0?fmt=jpeg&hei=1800&wid=1800",
    filters: ["Telfar", "Coach", "Marc Jacobs", "Longchamp", "Christian Dior"]
  },
  watches: {
    slug: "watches",
    label: "Watches",
    description: "Automatic, sport, and collectible watches from trusted makers.",
    imageUrl:
      "https://www.tissotwatches.com/dw/image/v2/BKKD_PRD/on/demandware.static/-/Sites-Tissot-Catalogue/default/dw95c4331d/product-pictures/63f42767-a9f5-4cdd-b952-8ea7b82b7e0c_T137-407-11-041-00_shadow.png?sh=1200&sm=cut&sw=1200",
    filters: ["Tissot", "Casio", "Seiko", "Citizen", "Swatch"]
  }
};

export function getCategoryMeta(slug: string): CategoryMeta {
  return (
    meta[slug] ?? {
      slug,
      label: slug,
      description: "Browse verified store products in this category.",
      imageUrl:
        "https://images.stockx.com/images/Air-Jordan-1-Retro-High-Element-Gore-Tex-Black-Particle-Grey.jpg?fit=fill&bg=FFFFFF&w=960&h=420&auto=compress&q=90&dpr=1",
      filters: []
    }
  );
}
