"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ApiError, api } from "@/lib/api";
import { passwordValidationMessage } from "@/lib/auth-flow";
import { ApiErrorStatus, AuthFlowStatus } from "@/components/auth/auth-flow-status";
import { AuthFlowShell } from "@/components/auth/auth-flow-shell";

export function ResetPasswordForm() {
  const token = useSearchParams().get("token");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [requestError, setRequestError] = useState<unknown>(null);
  const invalidLink = !token || token.length < 32 || token.length > 512;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting || invalidLink) return;
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password") ?? "");
    const confirmation = String(form.get("password_confirmation") ?? "");
    const passwordError = passwordValidationMessage(password);
    if (passwordError || password !== confirmation) {
      setValidationError(passwordError ?? "Passwords must match.");
      return;
    }

    setSubmitting(true);
    setValidationError(null);
    setRequestError(null);
    try {
      await api.confirmPasswordReset({ token, new_password: password });
      setSuccess(true);
    } catch (error) {
      setRequestError(error);
    } finally {
      setSubmitting(false);
    }
  }

  if (invalidLink) {
    return (
      <AuthFlowShell eyebrow="Account recovery" title="This reset link is not valid" description="The link is missing its secure reset token. Request a new link to continue.">
        <AuthFlowStatus tone="error" title="Invalid reset link">This link cannot be used to reset a password.</AuthFlowStatus>
        <div className="flex flex-col gap-3 sm:flex-row">
          <Link href="/forgot-password" className="bg-ink-900 px-4 py-3 text-center text-sm font-bold text-white hover:bg-market-green">Request a new reset</Link>
          <Link href="/login" className="border border-ink-300 px-4 py-3 text-center text-sm font-bold hover:border-ink-900">Return to login</Link>
        </div>
      </AuthFlowShell>
    );
  }

  if (success) {
    return (
      <AuthFlowShell eyebrow="Account recovery" title="Password updated" description="Your password was changed and existing sessions were revoked to protect your account.">
        <AuthFlowStatus tone="success" title="You can log in now">Use your new password the next time you sign in.</AuthFlowStatus>
        <Link href="/login" className="bg-ink-900 px-4 py-3 text-center text-sm font-bold text-white hover:bg-market-green">Log in with the new password</Link>
      </AuthFlowShell>
    );
  }

  const tokenFailure = requestError instanceof ApiError && requestError.kind === "invalid-action-token";
  return (
    <AuthFlowShell eyebrow="Account recovery" title="Choose a new password" description="Use 8–128 characters. Submitting this form revokes existing sessions for your account.">
      <form onSubmit={(event) => void submit(event)} className="grid gap-5" noValidate>
        <label className="grid gap-2 text-sm font-semibold">New password<input name="password" type="password" autoComplete="new-password" required minLength={8} maxLength={128} className="border border-ink-200 px-3 py-3 font-normal" /></label>
        <label className="grid gap-2 text-sm font-semibold">Confirm new password<input name="password_confirmation" type="password" autoComplete="new-password" required minLength={8} maxLength={128} className="border border-ink-200 px-3 py-3 font-normal" /></label>
        {validationError ? <AuthFlowStatus tone="error" title="Check your password">{validationError}</AuthFlowStatus> : null}
        {tokenFailure ? (
          <AuthFlowStatus tone="error" title="This reset link cannot be used"><p>It may be invalid, expired, or already used.</p><p className="mt-2"><Link href="/forgot-password" className="font-bold underline">Request a new reset</Link> or <Link href="/login" className="font-bold underline">return to login</Link>.</p></AuthFlowStatus>
        ) : requestError ? <ApiErrorStatus error={requestError} fallback="Your password could not be reset." /> : null}
        <button type="submit" disabled={submitting} aria-busy={submitting} className="bg-ink-900 px-5 py-3 text-sm font-bold text-white hover:bg-market-green disabled:cursor-not-allowed disabled:opacity-60">{submitting ? "Updating…" : "Update password"}</button>
      </form>
    </AuthFlowShell>
  );
}
