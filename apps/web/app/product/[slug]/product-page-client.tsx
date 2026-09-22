"use client";

import { Breadcrumbs } from "@/components/catalog/breadcrumbs";
import { ProductDetailView } from "@/components/catalog/product-detail-view";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { useApiResource } from "@/hooks/use-api-resource";
import { api } from "@/lib/api";

export function ProductPageClient({ slug }: { slug: string }) {
  const product = useApiResource(() => api.getProduct(slug), [slug]);

  return (
    <div className="page-shell grid gap-8 py-8">
      {product.status === "success" ? (
        <Breadcrumbs
          items={[
            { label: product.data.category.name, href: `/category/${product.data.category.slug}` },
            { label: product.data.name }
          ]}
        />
      ) : null}
      {product.status === "loading" || product.status === "idle" ? <LoadingState label="Loading product..." /> : null}
      {product.status === "error" ? (
        <ErrorState
          title="Product not found"
          message={product.error.message}
          href="/category/sneakers"
          action="Browse products"
        />
      ) : null}
      {product.status === "success" ? <ProductDetailView product={product.data} /> : null}
    </div>
  );
}
