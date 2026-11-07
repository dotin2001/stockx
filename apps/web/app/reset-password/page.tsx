import { Suspense } from "react";
import { ResetPasswordForm } from "@/components/auth/reset-password-form";
import { LoadingState } from "@/components/ui/states";

export default function ResetPasswordPage() {
  return <div className="page-shell py-8 sm:py-12"><Suspense fallback={<LoadingState label="Loading reset link…" />}><ResetPasswordForm /></Suspense></div>;
}
