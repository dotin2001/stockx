import { ProtectedGate } from "@/components/auth/protected-gate";
import { OrderDetailClient } from "@/components/orders/order-detail-client";

export default async function OrderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <div className="page-shell py-8"><ProtectedGate redirectTo={`/orders/${id}`}><OrderDetailClient orderId={id} /></ProtectedGate></div>;
}
