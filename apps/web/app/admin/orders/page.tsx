import { Suspense } from "react";
import { AdminOrdersPanel } from "@/components/admin/admin-orders-panel";
import { LoadingState } from "@/components/ui/states";

export default function AdminOrdersPage() {
  return (
    <div className="page-shell py-8">
      <Suspense fallback={<LoadingState label="Loading orders..." />}>
        <AdminOrdersPanel />
      </Suspense>
    </div>
  );
}
