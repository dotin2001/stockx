import { ProtectedGate } from "@/components/auth/protected-gate";
import { OrderHistoryClient } from "@/components/orders/order-history-client";

export default function OrdersPage() {
  return <div className="page-shell py-8"><ProtectedGate redirectTo="/orders"><OrderHistoryClient /></ProtectedGate></div>;
}
