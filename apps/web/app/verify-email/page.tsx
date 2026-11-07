import { Suspense } from "react";
import { VerifyEmailPanel } from "@/components/auth/verify-email-panel";
import { LoadingState } from "@/components/ui/states";

export default function VerifyEmailPage() {
  return <div className="page-shell py-8 sm:py-12"><Suspense fallback={<LoadingState label="Loading verification link…" />}><VerifyEmailPanel /></Suspense></div>;
}
