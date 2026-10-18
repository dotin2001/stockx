import { Suspense } from "react";
import { AdminOrderDetailPanel } from "@/components/admin/admin-order-detail-panel";
import { LoadingState } from "@/components/ui/states";

export default async function AdminOrderDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className="page-shell py-8">
      <Suspense fallback={<LoadingState label="Loading order review..." />}>
        <AdminOrderDetailPanel orderId={id} />
      </Suspense>
    </div>
  );
}
