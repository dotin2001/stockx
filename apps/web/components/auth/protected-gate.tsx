"use client";

import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { LoadingState } from "@/components/ui/states";

export function ProtectedGate({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();

  if (status === "checking") {
    return <LoadingState label="Checking your session..." />;
  }

  if (status !== "authenticated") {
    return (
      <div className="surface mx-auto max-w-xl px-6 py-10 text-center">
        <h1 className="text-3xl font-black">Login required</h1>
        <p className="mt-3 text-sm leading-6 text-ink-500">Sign in to access account, cart, checkout, and store message actions.</p>
        <Link href="/login" className="mt-6 inline-flex bg-market-green px-5 py-3 text-sm font-bold text-white hover:bg-ink-900">
          Log in
        </Link>
      </div>
    );
  }

  return <>{children}</>;
}
