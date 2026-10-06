import { Suspense } from "react";
import { AuthForm } from "@/components/auth/auth-form";
import { LoadingState } from "@/components/ui/states";

export default function SignupPage() {
  return (
    <div className="page-shell py-10">
      <Suspense fallback={<LoadingState label="Loading signup..." />}>
        <AuthForm mode="signup" />
      </Suspense>
    </div>
  );
}
