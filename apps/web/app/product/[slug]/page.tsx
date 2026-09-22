import { ProductPageClient } from "@/app/product/[slug]/product-page-client";

export default async function ProductPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <ProductPageClient slug={slug} />;
}
