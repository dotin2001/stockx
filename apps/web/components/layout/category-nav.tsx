import Link from "next/link";

const categories = [
  { label: "Sneakers", href: "/category/sneakers" },
  { label: "Streetwear", href: "/category/streetwear" },
  { label: "Trading Cards", href: "/category/trading-cards" },
  { label: "Collectibles", href: "/category/collectibles" },
  { label: "Handbags", href: "/category/handbags" },
  { label: "Watches", href: "/category/watches" }
];

export function CategoryNav() {
  return (
    <nav aria-label="Marketplace categories" className="border-b border-ink-200 bg-white">
      <div className="page-shell flex gap-6 overflow-x-auto py-3 text-sm font-semibold uppercase tracking-wide text-ink-700">
        {categories.map((category) => (
          <Link key={category.href} href={category.href} className="shrink-0 transition hover:text-market-green">
            {category.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
