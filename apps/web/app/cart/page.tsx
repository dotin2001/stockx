import { Suspense } from "react";
import { CartPageClient } from "@/components/cart/cart-page-client";
import { LoadingState } from "@/components/ui/states";

export default function CartPage() {
  return (
    <div className="page-shell py-8">
      <Suspense fallback={<LoadingState label="Loading cart..." />}>
        <CartPageClient />
      </Suspense>
    </div>
  );
}
