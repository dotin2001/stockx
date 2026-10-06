import type { ProductDiscoveryQueryParams, ProductDiscoverySort } from "@/lib/types";

const SORT_VALUES = new Set<ProductDiscoverySort>(["newest", "price_asc", "price_desc", "popular", "name_asc"]);
const DISCOVERY_KEYS = ["brand", "size", "min_price", "max_price", "available_only", "sort", "limit", "offset"];

type ReadableSearchParams = {
  get(name: string): string | null;
  getAll(name: string): string[];
  toString(): string;
};

function positiveInteger(value: string | null) {
  if (!value) {
    return null;
  }
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : null;
}

function positiveLimit(value: string | null) {
  const parsed = positiveInteger(value);
  return parsed && parsed > 0 ? parsed : null;
}

function uniqueValues(values: string[]) {
  const seen = new Set<string>();
  return values
    .map((value) => value.trim())
    .filter((value) => {
      const key = value.toLowerCase();
      if (!value || seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
}

export function parseDiscoveryParams(params: ReadableSearchParams, defaultSort: ProductDiscoverySort = "newest"): ProductDiscoveryQueryParams {
  const rawSort = params.get("sort") as ProductDiscoverySort | null;
  const sort = rawSort && SORT_VALUES.has(rawSort) ? rawSort : defaultSort;
  const q = params.get("q")?.trim() || null;

  return {
    q,
    brand: uniqueValues(params.getAll("brand")),
    size: uniqueValues(params.getAll("size")),
    min_price: positiveInteger(params.get("min_price")),
    max_price: positiveInteger(params.get("max_price")),
    available_only: ["true", "1", "yes"].includes((params.get("available_only") ?? "").toLowerCase()),
    sort,
    limit: positiveLimit(params.get("limit")) ?? undefined,
    offset: positiveInteger(params.get("offset")) ?? undefined
  };
}

export function discoveryParamsKey(params: ProductDiscoveryQueryParams) {
  return JSON.stringify({
    q: params.q ?? null,
    brand: params.brand ?? [],
    size: params.size ?? [],
    min_price: params.min_price ?? null,
    max_price: params.max_price ?? null,
    available_only: params.available_only ?? false,
    sort: params.sort ?? "newest",
    limit: params.limit ?? null,
    offset: params.offset ?? null
  });
}

export function hasActiveDiscoveryFilters(params: ProductDiscoveryQueryParams) {
  return Boolean(
    (params.brand?.length ?? 0) > 0 ||
      (params.size?.length ?? 0) > 0 ||
      (params.min_price !== undefined && params.min_price !== null) ||
      (params.max_price !== undefined && params.max_price !== null) ||
      params.available_only
  );
}

export function nextDiscoveryHref(pathname: string, current: ReadableSearchParams, updates: ProductDiscoveryQueryParams) {
  const params = new URLSearchParams(current.toString());
  for (const key of DISCOVERY_KEYS) {
    params.delete(key);
  }

  const merged = {
    ...parseDiscoveryParams(current),
    ...updates
  };

  for (const brand of merged.brand ?? []) {
    params.append("brand", brand);
  }
  for (const size of merged.size ?? []) {
    params.append("size", size);
  }
  if (merged.min_price !== undefined && merged.min_price !== null) {
    params.set("min_price", String(merged.min_price));
  }
  if (merged.max_price !== undefined && merged.max_price !== null) {
    params.set("max_price", String(merged.max_price));
  }
  if (merged.available_only) {
    params.set("available_only", "true");
  }
  if (merged.sort && merged.sort !== "newest") {
    params.set("sort", merged.sort);
  }
  if (merged.limit) {
    params.set("limit", String(merged.limit));
  }
  if (merged.offset) {
    params.set("offset", String(merged.offset));
  }

  const query = params.toString();
  return query ? `${pathname}?${query}` : pathname;
}

export function clearDiscoveryHref(pathname: string, current: ReadableSearchParams) {
  const params = new URLSearchParams(current.toString());
  for (const key of DISCOVERY_KEYS) {
    params.delete(key);
  }
  const query = params.toString();
  return query ? `${pathname}?${query}` : pathname;
}

export function toggleValue(values: string[] | undefined, value: string) {
  const current = values ?? [];
  return current.includes(value) ? current.filter((item) => item !== value) : [...current, value];
}
