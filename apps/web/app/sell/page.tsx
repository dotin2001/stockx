import Link from "next/link";

export default function SellPage() {
  return (
    <div className="page-shell py-8">
      <section className="surface mx-auto grid max-w-2xl gap-5 p-6">
        <div>
          <p className="text-sm font-bold uppercase tracking-wide text-market-green">Store-managed selling</p>
          <h1 className="mt-2 text-3xl font-black">Selling is managed by the store</h1>
          <p className="mt-3 text-sm leading-6 text-ink-500">
            Customer accounts are for shopping, carts, watchlists, checkout, and contacting the store team. Catalog products and sellable inventory are managed by store admins.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link href="/category/sneakers" className="bg-market-green px-5 py-3 text-sm font-bold text-white hover:bg-ink-900">
            Browse Products
          </Link>
          <Link href="/account" className="border border-ink-900 px-5 py-3 text-sm font-bold text-ink-900 hover:bg-ink-900 hover:text-white">
            Message Store Admin
          </Link>
        </div>
      </section>
    </div>
  );
}
