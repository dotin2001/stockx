"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { ProductDetail } from "@/lib/types";

export function ProductDetailView({ product }: { product: ProductDetail }) {
  const { status, accessToken } = useAuth();
  const [watchMessage, setWatchMessage] = useState<string | null>(null);
  const [watching, setWatching] = useState(false);

  async function addToWatchlist() {
    if (!accessToken) {
      setWatchMessage("Log in to watch this product.");
      return;
    }
    setWatching(true);
    setWatchMessage(null);
    try {
      await api.addWatchlist(accessToken, product.id);
      setWatchMessage("Added to your watchlist.");
    } catch (error) {
      setWatchMessage(error instanceof ApiError ? error.message : "Could not update watchlist.");
    } finally {
      setWatching(false);
    }
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_420px]">
      <section className="surface grid place-items-center bg-white p-8">
        {product.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={product.image_url} alt={product.name} className="max-h-[460px] object-contain" />
        ) : (
          <div className="grid h-64 w-full place-items-center bg-ink-100 text-sm font-bold uppercase text-ink-500">No image</div>
        )}
      </section>
      <aside className="surface p-6">
        <p className="text-sm font-bold uppercase tracking-wide text-market-green">{product.brand ?? product.category.name}</p>
        <h1 className="mt-3 text-3xl font-black leading-tight">{product.name}</h1>
        <p className="mt-4 text-sm leading-6 text-ink-500">{product.description ?? "Verified marketplace product."}</p>
        <div className="mt-8 grid grid-cols-2 gap-3 border-y border-ink-200 py-5">
          <div>
            <p className="text-xs text-ink-500">Lowest Ask</p>
            <p className="text-2xl font-black">{formatMoney(product.lowest_ask_cents)}</p>
          </div>
          <div>
            <p className="text-xs text-ink-500">Sold</p>
            <p className="text-2xl font-black">{product.total_sold}</p>
          </div>
        </div>
        {product.variants.length > 0 ? (
          <div className="mt-6">
            <h2 className="text-sm font-bold uppercase tracking-wide">Variants</h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {product.variants.map((variant) => (
                <span key={variant.id} className="border border-ink-200 px-3 py-2 text-sm">
                  {[variant.size, variant.color].filter(Boolean).join(" / ") || variant.sku || "Variant"}
                </span>
              ))}
            </div>
          </div>
        ) : null}
        <div className="mt-8 grid gap-3">
          {status === "authenticated" ? (
            <>
              <button type="button" onClick={addToWatchlist} disabled={watching} className="bg-ink-900 px-5 py-3 text-sm font-bold text-white hover:bg-market-green disabled:cursor-not-allowed disabled:opacity-60">
                {watching ? "Adding..." : "Add to Watchlist"}
              </button>
              <Link href={`/sell?product=${product.slug}`} className="border border-ink-900 px-5 py-3 text-center text-sm font-bold text-ink-900 hover:bg-ink-900 hover:text-white">
                Sell This Product
              </Link>
            </>
          ) : (
            <Link href="/login" className="bg-market-green px-5 py-3 text-center text-sm font-bold text-white hover:bg-ink-900">
              Log in to Watch or Sell
            </Link>
          )}
          {watchMessage ? <p className="text-sm font-semibold text-ink-600">{watchMessage}</p> : null}
        </div>
      </aside>
    </div>
  );
}
