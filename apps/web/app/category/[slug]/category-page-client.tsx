"use client";

import { Breadcrumbs } from "@/components/catalog/breadcrumbs";
import { CategoryHero } from "@/components/catalog/category-hero";
import { CategorySideNav } from "@/components/catalog/category-side-nav";
import { ProductGrid } from "@/components/catalog/product-grid";
import { ScrollToTop } from "@/components/motion/scroll-to-top";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { useApiResource } from "@/hooks/use-api-resource";
import { api } from "@/lib/api";
import { getCategoryMeta } from "@/lib/category-meta";

export function CategoryPageClient({ slug }: { slug: string }) {
  const meta = getCategoryMeta(slug);
  const products = useApiResource(() => api.listCategoryProducts(slug, 48), [slug]);

  return (
    <>
      <CategoryHero meta={meta} />
      <div className="page-shell grid gap-8 py-8">
        <Breadcrumbs items={[{ label: meta.label }]} />
        <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
          <CategorySideNav meta={meta} />
          <section className="grid gap-5">
            <div>
              <h1 className="text-2xl font-black">{meta.label}</h1>
              <p className="mt-1 text-sm text-ink-500">API-backed products for this category.</p>
            </div>
            {products.status === "loading" || products.status === "idle" ? <LoadingState /> : null}
            {products.status === "error" ? (
              <ErrorState title="Category unavailable" message={products.error.message} href="/" />
            ) : null}
            {products.status === "success" ? (
              <ProductGrid products={products.data.items} emptyTitle="No products in this category" />
            ) : null}
          </section>
        </div>
      </div>
      <ScrollToTop />
    </>
  );
}
