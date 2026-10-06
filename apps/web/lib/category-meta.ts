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
  }
};

export function getCategoryMeta(slug: string): CategoryMeta {
  return (
    meta[slug] ?? {
      slug,
      label: slug,
      description: "Browse verified marketplace products in this category.",
      imageUrl:
        "https://images.stockx.com/images/Air-Jordan-1-Retro-High-Element-Gore-Tex-Black-Particle-Grey.jpg?fit=fill&bg=FFFFFF&w=960&h=420&auto=compress&q=90&dpr=1",
      filters: []
    }
  );
}
