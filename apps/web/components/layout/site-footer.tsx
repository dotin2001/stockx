import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-ink-200 bg-white">
      <div className="page-shell grid gap-8 py-10 md:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <h2 className="text-lg font-bold">StockX Store</h2>
          <p className="mt-3 max-w-md text-sm leading-6 text-ink-500">
            Browse verified store products, follow prices, and keep your cart ready while the store team manages the catalog.
          </p>
        </div>
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wide">Browse</h3>
          <div className="mt-3 grid gap-2 text-sm text-ink-600">
            <Link href="/category/sneakers">Sneakers</Link>
            <Link href="/category/streetwear">Streetwear</Link>
            <Link href="/category/collectibles">Collectibles</Link>
          </div>
        </div>
        <div>
          <h3 className="text-sm font-bold uppercase tracking-wide">Account</h3>
          <div className="mt-3 grid gap-2 text-sm text-ink-600">
            <Link href="/login">Login</Link>
            <Link href="/signup">Sign Up</Link>
            <Link href="/account">Account</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
