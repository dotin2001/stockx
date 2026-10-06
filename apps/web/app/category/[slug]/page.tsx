import { CategoryPageClient } from "@/app/category/[slug]/category-page-client";

export default async function CategoryPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <CategoryPageClient slug={slug} />;
}
