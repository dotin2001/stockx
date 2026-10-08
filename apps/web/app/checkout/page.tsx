import { CheckoutPageClient } from "@/components/checkout/checkout-page-client";
import { ProtectedGate } from "@/components/auth/protected-gate";

export default function CheckoutPage() {
  return (
    <div className="page-shell py-8">
      <ProtectedGate redirectTo="/checkout">
        <CheckoutPageClient />
      </ProtectedGate>
    </div>
  );
}
