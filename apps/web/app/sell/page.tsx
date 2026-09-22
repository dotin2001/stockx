import { ProtectedGate } from "@/components/auth/protected-gate";
import { SellForm } from "@/components/auth/sell-form";

export default async function SellPage({
  searchParams
}: {
  searchParams: Promise<{ product?: string | string[] }>;
}) {
  const params = await searchParams;
  const requestedProduct = Array.isArray(params.product) ? params.product[0] : params.product;

  return (
    <div className="page-shell py-8">
      <ProtectedGate>
        <SellForm requestedProduct={requestedProduct} />
      </ProtectedGate>
    </div>
  );
}
