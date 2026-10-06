import { AccountDashboard } from "@/components/auth/account-dashboard";
import { ProtectedGate } from "@/components/auth/protected-gate";

export default function AccountPage() {
  return (
    <div className="page-shell py-8">
      <ProtectedGate>
        <AccountDashboard />
      </ProtectedGate>
    </div>
  );
}
