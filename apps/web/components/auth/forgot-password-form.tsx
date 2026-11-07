"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { ApiError, api } from "@/lib/api";
import { DEFAULT_SUCCESS_COOLDOWN_SECONDS, isValidEmail } from "@/lib/auth-flow";
import { useCooldown } from "@/hooks/use-cooldown";
import { ApiErrorStatus, AuthFlowStatus } from "@/components/auth/auth-flow-status";
import { AuthFlowShell } from "@/components/auth/auth-flow-shell";

export function ForgotPasswordForm() {
  const [submitting, setSubmitting] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [requestError, setRequestError] = useState<unknown>(null);
  const { remaining, start } = useCooldown();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting || remaining > 0) return;
    const email = String(new FormData(event.currentTarget).get("email") ?? "").trim();
    if (!isValidEmail(email)) {
      setValidationError("Enter a valid email address.");
      return;
    }

    setSubmitting(true);
    setAccepted(false);
    setValidationError(null);
    setRequestError(null);
    try {
      await api.requestPasswordReset({ email });
      setAccepted(true);
      start(DEFAULT_SUCCESS_COOLDOWN_SECONDS);
    } catch (error) {
      if (error instanceof ApiError && error.kind === "rate-limited") {
        start(error.retryAfterSeconds ?? 60);
      }
      setRequestError(error);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthFlowShell eyebrow="Account recovery" title="Reset your password" description="Enter your account email. For privacy, the confirmation is the same whether or not an account matches.">
      <form onSubmit={(event) => void submit(event)} className="grid gap-5" noValidate>
        <label className="grid gap-2 text-sm font-semibold text-ink-900">
          Email address
          <input name="email" type="email" autoComplete="email" required aria-describedby="recovery-help" className="border border-ink-200 px-3 py-3 font-normal" />
        </label>
        <p id="recovery-help" className="text-xs leading-5 text-ink-500">If the account is eligible, password-reset instructions will be sent.</p>
        {validationError ? <AuthFlowStatus tone="error" title="Check your email">{validationError}</AuthFlowStatus> : null}
        {accepted ? <AuthFlowStatus tone="success" title="Check your email">If the account is eligible, password-reset instructions have been sent.</AuthFlowStatus> : null}
        {requestError instanceof ApiError && requestError.kind === "rate-limited" ? (
          <AuthFlowStatus tone="warning" title="Please wait">Try again in {remaining} second{remaining === 1 ? "" : "s"}.</AuthFlowStatus>
        ) : requestError ? <ApiErrorStatus error={requestError} fallback="The reset request could not be sent." /> : null}
        <button type="submit" disabled={submitting || remaining > 0} aria-busy={submitting} className="bg-ink-900 px-5 py-3 text-sm font-bold text-white hover:bg-market-green disabled:cursor-not-allowed disabled:opacity-60">
          {submitting ? "Sending…" : remaining > 0 ? `Try again in ${remaining}s` : "Send reset instructions"}
        </button>
      </form>
      <Link href="/login" className="text-sm font-bold text-ink-700 underline decoration-ink-300 underline-offset-4 hover:text-market-green">Return to login</Link>
    </AuthFlowShell>
  );
}
