import { SearchPageClient } from "@/app/search/search-page-client";

export default async function SearchPage({
  searchParams
}: {
  searchParams: Promise<{ q?: string | string[] }>;
}) {
  const params = await searchParams;
  const rawQuery = Array.isArray(params.q) ? params.q[0] : params.q;
  return <SearchPageClient query={(rawQuery ?? "").trim()} />;
}
