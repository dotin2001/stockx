"use client";

import { useMemo } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { DiscoveryControls } from "@/components/catalog/discovery-controls";
import { ProductGrid } from "@/components/catalog/product-grid";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";
import { useApiResource } from "@/hooks/use-api-resource";
import { api } from "@/lib/api";
import type { ProductPage } from "@/lib/types";
import { clearDiscoveryHref, discoveryParamsKey, hasActiveDiscoveryFilters, parseDiscoveryParams } from "@/lib/discovery-params";

function emptyProductPage(limit: number, offset: number): ProductPage {
  return {
    items: [],
    total: 0,
    limit,
    offset,
    discovery: {
      selected: {
        q: null,
        category_slug: null,
        brands: [],
        sizes: [],
        min_price_cents: null,
        max_price_cents: null,
        available_only: false
      },
      sort: "name_asc",
      brands: [],
      sizes: [],
      price_bounds: { min_cents: null, max_cents: null },
      total: 0,
      limit,
      offset
    }
  };
}

export function SearchPageClient() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const paramsKey = searchParams.toString();
  const discovery = useMemo(() => parseDiscoveryParams(new URLSearchParams(paramsKey), "name_asc"), [paramsKey]);
  const query = discovery.q ?? "";
  const discoveryKey = discoveryParamsKey(discovery);
  const results = useApiResource(
    () =>
      query
        ? api.searchProducts(query, discovery.limit ?? 48, discovery.offset ?? 0, discovery)
        : Promise.resolve(emptyProductPage(discovery.limit ?? 48, discovery.offset ?? 0)),
    [query, discoveryKey]
  );
  const hasFilters = hasActiveDiscoveryFilters(discovery);

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
        <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
          <DiscoveryControls metadata={results.data.discovery} />
          <div className="grid gap-5">
            <p className="text-sm font-semibold text-ink-500">{results.data.total} products found</p>
            {results.data.items.length === 0 && hasFilters ? (
              <EmptyState
                title="No products match these filters"
                message="Clear filters or broaden the price, brand, size, or availability selections."
                href={clearDiscoveryHref(pathname, searchParams)}
                action="Clear filters"
              />
            ) : (
              <ProductGrid
                products={results.data.items}
                emptyTitle="No matches found"
                emptyMessage="Try a different brand, category, or product name."
              />
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
