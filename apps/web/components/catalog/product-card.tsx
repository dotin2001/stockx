import Link from "next/link";
import type { ProductSummary } from "@/lib/types";
import { formatCount, formatMoney } from "@/lib/format";

export function ProductCard({ product }: { product: ProductSummary }) {
  return (
    <Link href={`/product/${product.slug}`} className="group surface flex min-h-[300px] flex-col overflow-hidden transition duration-200 hover:-translate-y-1 hover:shadow-lift">
      <div className="grid aspect-[4/3] place-items-center bg-white p-6">
        {product.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={product.image_url} alt={product.name} className="max-h-44 object-contain transition duration-300 group-hover:scale-105" />
        ) : (
          <div className="grid h-32 w-32 place-items-center bg-ink-100 text-xs font-bold uppercase text-ink-500">No image</div>
        )}
      </div>
      <div className="flex flex-1 flex-col border-t border-ink-200 p-4">
        <p className="text-xs font-bold uppercase tracking-wide text-market-green">{product.brand ?? product.category.name}</p>
        <h3 className="mt-2 line-clamp-2 min-h-12 text-sm font-bold uppercase leading-6 text-ink-900">{product.name}</h3>
        <div className="mt-auto flex items-end justify-between gap-4 pt-5">
          <div>
            <p className="text-xs text-ink-500">Lowest Ask</p>
            <p className="text-lg font-bold">{formatMoney(product.lowest_ask_cents)}</p>
          </div>
          <p className="text-xs text-ink-500">{formatCount(product.total_sold)} Sold</p>
        </div>
      </div>
    </Link>
  );
}
