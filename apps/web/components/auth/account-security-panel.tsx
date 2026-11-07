"use client";

import { useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import { DEFAULT_SUCCESS_COOLDOWN_SECONDS } from "@/lib/auth-flow";
import { useCooldown } from "@/hooks/use-cooldown";
import { ApiErrorStatus, AuthFlowStatus } from "@/components/auth/auth-flow-status";

export function AccountSecurityPanel() {
  const { user, logoutAll } = useAuth();
  const [resending, setResending] = useState(false);
  const [resendAccepted, setResendAccepted] = useState(false);
  const [resendError, setResendError] = useState<unknown>(null);
  const [confirmingLogoutAll, setConfirmingLogoutAll] = useState(false);
  const [loggingOutAll, setLoggingOutAll] = useState(false);
  const [logoutError, setLogoutError] = useState<unknown>(null);
  const { remaining, start } = useCooldown();

  if (!user) return null;

  async function resendVerification() {
    if (!user || user.is_verified || resending || remaining > 0) return;
    setResending(true);
    setResendAccepted(false);
    setResendError(null);
    try {
      await api.requestVerification({ email: user.email });
      setResendAccepted(true);
      start(DEFAULT_SUCCESS_COOLDOWN_SECONDS);
    } catch (error) {
      if (error instanceof ApiError && error.kind === "rate-limited") start(error.retryAfterSeconds ?? 60);
      setResendError(error);
    } finally {
      setResending(false);
    }
  }

  async function confirmLogoutAll() {
    if (loggingOutAll) return;
    setLoggingOutAll(true);
    setLogoutError(null);
    try {
      await logoutAll();
    } catch (error) {
      setLogoutError(error);
      setLoggingOutAll(false);
    }
  }

  return (
    <section className="surface grid gap-6 p-5 sm:p-6" aria-labelledby="account-security-heading">
      <div>
        <p className="text-sm font-bold uppercase tracking-wide text-market-green">Security</p>
        <h2 id="account-security-heading" className="mt-2 text-xl font-black">Email and sessions</h2>
      </div>

      <div className="grid gap-3 border border-ink-200 p-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="font-bold">Email status</h3>
            <p className="mt-1 text-sm text-ink-500">{user.email}</p>
          </div>
          <span className={`w-fit px-3 py-1 text-xs font-bold ${user.is_verified ? "bg-market-mint text-ink-800" : "bg-amber-100 text-amber-950"}`}>
            {user.is_verified ? "Verified" : "Unverified"}
          </span>
        </div>
        {!user.is_verified ? (
          <div className="grid gap-3">
            <p className="text-sm leading-6 text-ink-600">Verify your email to keep your account recovery details current.</p>
            {resendAccepted ? <AuthFlowStatus tone="success" title="Check your email">If the account is eligible, verification instructions have been sent.</AuthFlowStatus> : null}
            {resendError instanceof ApiError && resendError.kind === "rate-limited" ? <AuthFlowStatus tone="warning" title="Please wait">You can request another message in {remaining} second{remaining === 1 ? "" : "s"}.</AuthFlowStatus> : resendError ? <ApiErrorStatus error={resendError} fallback="The verification message could not be sent." /> : null}
            <button type="button" onClick={() => void resendVerification()} disabled={resending || remaining > 0} aria-busy={resending} className="w-fit border border-ink-900 px-4 py-2 text-sm font-bold hover:bg-ink-900 hover:text-white disabled:cursor-not-allowed disabled:opacity-60">
              {resending ? "Sending…" : remaining > 0 ? `Resend in ${remaining}s` : "Resend verification email"}
            </button>
          </div>
        ) : <p className="text-sm text-ink-600">Your email address is verified.</p>}
      </div>

      <div className="grid gap-3 border border-market-red/30 p-4">
        <div>
          <h3 className="font-bold">Log out all devices</h3>
          <p className="mt-1 text-sm leading-6 text-ink-500">End every active refresh session, including this one.</p>
        </div>
        {logoutError ? <ApiErrorStatus error={logoutError} fallback="All-device logout failed. Your current session has been preserved." /> : null}
        {confirmingLogoutAll ? (
          <div role="group" aria-labelledby="logout-all-confirmation" className="grid gap-3 bg-red-50 p-3">
            <p id="logout-all-confirmation" className="text-sm font-bold text-market-red">Are you sure you want to log out every device?</p>
            <div className="flex flex-col gap-2 sm:flex-row">
              <button type="button" onClick={() => void confirmLogoutAll()} disabled={loggingOutAll} aria-busy={loggingOutAll} className="bg-market-red px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-60">{loggingOutAll ? "Logging out…" : "Yes, log out all devices"}</button>
              <button type="button" onClick={() => setConfirmingLogoutAll(false)} disabled={loggingOutAll} className="border border-ink-300 px-4 py-2 text-sm font-bold hover:border-ink-900 disabled:opacity-60">Cancel</button>
            </div>
          </div>
        ) : (
          <button type="button" onClick={() => { setLogoutError(null); setConfirmingLogoutAll(true); }} className="w-fit border border-market-red px-4 py-2 text-sm font-bold text-market-red hover:bg-market-red hover:text-white">Log out all devices</button>
        )}
      </div>
    </section>
  );
}
