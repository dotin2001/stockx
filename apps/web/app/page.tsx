"use client";

import Link from "next/link";
import { useMemo } from "react";
import { api } from "@/lib/api";
import { useApiResource } from "@/hooks/use-api-resource";
import { HeroTicker } from "@/components/motion/hero-ticker";
import { Reveal } from "@/components/motion/reveal";
import { ProductGrid } from "@/components/catalog/product-grid";
import { LoadingState, ErrorState } from "@/components/ui/states";

export default function HomePage() {
  const products = useApiResource(() => api.listProducts(24), []);
  const grouped = useMemo(() => {
    if (products.status !== "success") {
      return {};
    }
    return products.data.items.reduce<Record<string, typeof products.data.items>>((acc, product) => {
      acc[product.category.slug] = [...(acc[product.category.slug] ?? []), product];
      return acc;
    }, {});
  }, [products]);

  return (
    <>
      <section className="bg-ink-900 text-white">
        <div className="page-shell grid min-h-[360px] place-items-center py-14 text-center">
          <div>
            <p className="text-sm font-bold uppercase tracking-[0.35em] text-white/70">Shop Verified Store Goods</p>
            <h1 className="mt-5 max-w-4xl text-5xl font-black uppercase leading-none sm:text-7xl">Verified style, live from the market</h1>
          </div>
        </div>
        <HeroTicker />
      </section>
      <div className="page-shell grid gap-12 py-12">
        {products.status === "loading" || products.status === "idle" ? <LoadingState /> : null}
        {products.status === "error" ? <ErrorState message={products.error.message} /> : null}
        {products.status === "success" ? (
          <>
            {[
              ["sneakers", "Most Popular Sneakers"],
              ["streetwear", "Popular Streetwear"],
              ["collectibles", "Trending Collectibles"]
            ].map(([slug, title]) => (
              <Reveal key={slug}>
                <section className="grid gap-5">
                  <div className="flex items-center justify-between gap-4">
                    <h2 className="text-2xl font-black">{title}</h2>
                    <Link href={`/category/${slug}`} className="text-sm font-bold text-market-green hover:text-ink-900">
                      See All
                    </Link>
                  </div>
                  <ProductGrid products={(grouped[slug] ?? []).slice(0, 4)} emptyTitle={`No ${title.toLowerCase()} yet`} />
                </section>
              </Reveal>
            ))}
            <Reveal>
              <section className="grid gap-4 border-y border-ink-200 py-10 md:grid-cols-3">
                {["Lowest asks update from the API", "Authenticated users can watch and cart", "Static pages remain as migration reference"].map((text) => (
                  <div key={text} className="surface p-5">
                    <h3 className="text-lg font-black">{text}</h3>
                    <p className="mt-3 text-sm leading-6 text-ink-500">A sharper store foundation without losing the original storefront rhythm.</p>
                  </div>
                ))}
              </section>
            </Reveal>
          </>
        ) : null}
      </div>
    </>
  );
}
