"use client";

import { ProductGrid } from "@/components/catalog/product-grid";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { useApiResource } from "@/hooks/use-api-resource";
import { api } from "@/lib/api";

export function SearchPageClient({ query }: { query: string }) {
  const results = useApiResource(
    () => (query ? api.searchProducts(query, 48) : Promise.resolve({ items: [], total: 0, limit: 48, offset: 0 })),
    [query]
  );

  return (
    <div className="page-shell grid gap-6 py-8">
      <div>
        <p className="text-sm font-bold uppercase tracking-wide text-market-green">Search</p>
        <h1 className="mt-2 text-3xl font-black">{query ? `Results for "${query}"` : "Search the store"}</h1>
      </div>
      {!query ? (
        <EmptyState
          title="Enter a search term"
          message="Use the search box in the header to find products by name, brand, or category."
        />
      ) : null}
      {query && (results.status === "loading" || results.status === "idle") ? <LoadingState label="Searching..." /> : null}
      {query && results.status === "error" ? <ErrorState title="Search failed" message={results.error.message} /> : null}
      {query && results.status === "success" ? (
        <ProductGrid
          products={results.data.items}
          emptyTitle="No matches found"
          emptyMessage="Try a different brand, category, or product name."
        />
      ) : null}
    </div>
  );
}
