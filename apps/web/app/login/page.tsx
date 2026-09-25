import { Suspense } from "react";
import { AuthForm } from "@/components/auth/auth-form";
import { LoadingState } from "@/components/ui/states";

export default function LoginPage() {
  return (
    <div className="page-shell py-10">
      <Suspense fallback={<LoadingState label="Loading login..." />}>
        <AuthForm mode="login" />
      </Suspense>
    </div>
  );
}
