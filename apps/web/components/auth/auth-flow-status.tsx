import type { ReactNode } from "react";
import { ApiError } from "@/lib/api";

type Tone = "success" | "error" | "warning" | "info";

const toneClasses: Record<Tone, string> = {
  success: "border-market-green/30 bg-market-mint text-ink-800",
  error: "border-market-red/30 bg-red-50 text-market-red",
  warning: "border-amber-300 bg-amber-50 text-amber-950",
  info: "border-ink-200 bg-ink-50 text-ink-700"
};

export function AuthFlowStatus({ tone, title, children }: { tone: Tone; title: string; children?: ReactNode }) {
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      aria-live={tone === "error" ? "assertive" : "polite"}
      className={`border px-4 py-3 text-sm ${toneClasses[tone]}`}
    >
      <p className="font-bold">{title}</p>
      {children ? <div className="mt-1 leading-6">{children}</div> : null}
    </div>
  );
}

export function ApiErrorStatus({ error, fallback = "Please try again." }: { error: unknown; fallback?: string }) {
  if (error instanceof ApiError && error.kind === "access-denied") {
    return <AuthFlowStatus tone="error" title="Access denied">Your account does not have permission to perform this action.</AuthFlowStatus>;
  }
  if (error instanceof ApiError && error.kind === "validation") {
    return <AuthFlowStatus tone="error" title="Check your information">{error.message}</AuthFlowStatus>;
  }
  return <AuthFlowStatus tone="error" title="Something went wrong">{error instanceof ApiError ? error.message : fallback}</AuthFlowStatus>;
}
