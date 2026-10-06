import { Suspense } from "react";
import { CategoryPageClient } from "@/app/category/[slug]/category-page-client";
import { LoadingState } from "@/components/ui/states";

export default async function CategoryPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return (
    <Suspense fallback={<div className="page-shell py-8"><LoadingState /></div>}>
      <CategoryPageClient slug={slug} />
    </Suspense>
  );
}
