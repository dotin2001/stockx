"use client";

import { useMemo } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { Breadcrumbs } from "@/components/catalog/breadcrumbs";
import { DiscoveryControls } from "@/components/catalog/discovery-controls";
import { CategoryHero } from "@/components/catalog/category-hero";
import { ProductGrid } from "@/components/catalog/product-grid";
import { ScrollToTop } from "@/components/motion/scroll-to-top";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { useApiResource } from "@/hooks/use-api-resource";
import { api } from "@/lib/api";
import { getCategoryMeta } from "@/lib/category-meta";
import { clearDiscoveryHref, discoveryParamsKey, hasActiveDiscoveryFilters, parseDiscoveryParams } from "@/lib/discovery-params";

export function CategoryPageClient({ slug }: { slug: string }) {
  const meta = getCategoryMeta(slug);
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const paramsKey = searchParams.toString();
  const discovery = useMemo(() => parseDiscoveryParams(new URLSearchParams(paramsKey)), [paramsKey]);
  const discoveryKey = discoveryParamsKey(discovery);
  const products = useApiResource(
    () => api.listCategoryProducts(slug, discovery.limit ?? 48, discovery.offset ?? 0, discovery),
    [slug, discoveryKey]
  );
  const hasFilters = hasActiveDiscoveryFilters(discovery);

  return (
    <>
      <CategoryHero meta={meta} />
      <div className="page-shell grid gap-8 py-8">
        <Breadcrumbs items={[{ label: meta.label }]} />
        <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
          {products.status === "success" ? <DiscoveryControls metadata={products.data.discovery} /> : <div />}
          <section className="grid gap-5">
            <div>
              <h1 className="text-2xl font-black">{meta.label}</h1>
              <p className="mt-1 text-sm text-ink-500">
                {products.status === "success" ? `${products.data.total} products found` : "Loading products for this category."}
              </p>
            </div>
            {products.status === "loading" || products.status === "idle" ? <LoadingState /> : null}
            {products.status === "error" ? (
              <ErrorState title="Category unavailable" message={products.error.message} href="/" />
            ) : null}
            {products.status === "success" && products.data.items.length === 0 && hasFilters ? (
              <EmptyState
                title="No products match these filters"
                message="Clear filters or broaden the price, brand, size, or availability selections."
                href={clearDiscoveryHref(pathname, searchParams)}
                action="Clear filters"
              />
            ) : null}
            {products.status === "success" && (products.data.items.length > 0 || !hasFilters) ? (
              <ProductGrid products={products.data.items} emptyTitle="No products in this category" />
            ) : null}
          </section>
        </div>
      </div>
      <ScrollToTop />
    </>
  );
}
