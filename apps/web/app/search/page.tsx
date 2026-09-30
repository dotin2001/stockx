import { Suspense } from "react";
import { SearchPageClient } from "@/app/search/search-page-client";
import { LoadingState } from "@/components/ui/states";

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="page-shell py-8"><LoadingState label="Loading search..." /></div>}>
      <SearchPageClient />
    </Suspense>
  );
}
