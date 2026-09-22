import type { ProductSummary } from "@/lib/types";
import { EmptyState } from "@/components/ui/states";
import { ProductCard } from "@/components/catalog/product-card";

export function ProductGrid({ products, emptyTitle = "No products found", emptyMessage = "Try another category or search term." }: { products: ProductSummary[]; emptyTitle?: string; emptyMessage?: string }) {
  if (products.length === 0) {
    return <EmptyState title={emptyTitle} message={emptyMessage} href="/category/sneakers" />;
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
}
