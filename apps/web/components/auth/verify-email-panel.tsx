"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/contexts/auth-context";
import type { UserPublic } from "@/lib/types";
import { ApiErrorStatus, AuthFlowStatus } from "@/components/auth/auth-flow-status";
import { AuthFlowShell } from "@/components/auth/auth-flow-shell";

const confirmationByToken = new Map<string, Promise<UserPublic>>();

export function confirmVerificationOnce(token: string) {
  const existing = confirmationByToken.get(token);
  if (existing) return existing;
  const confirmation = api.confirmVerification({ token });
  confirmationByToken.set(token, confirmation);
  return confirmation;
}

export function VerifyEmailPanel() {
  const token = useSearchParams().get("token");
  const { user, updateUserIfMatches } = useAuth();
  const invalidToken = !token || token.length < 32 || token.length > 512;
  const [state, setState] = useState<"loading" | "success" | "token-error" | "error">(invalidToken ? "token-error" : "loading");
  const [updatedCurrentUser, setUpdatedCurrentUser] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (invalidToken || !token) return;
    let active = true;
    void confirmVerificationOnce(token).then((confirmedUser) => {
      if (!active) return;
      setUpdatedCurrentUser(updateUserIfMatches(confirmedUser));
      setState("success");
    }).catch((caught: unknown) => {
      if (!active) return;
      setError(caught);
      setState(caught instanceof ApiError && caught.kind === "invalid-action-token" ? "token-error" : "error");
    });
    return () => { active = false; };
  }, [invalidToken, token, updateUserIfMatches]);

  return (
    <AuthFlowShell eyebrow="Email verification" title={state === "success" ? "Email verified" : state === "loading" ? "Verifying your email" : "This verification link cannot be used"} description={state === "loading" ? "Keep this page open while the secure link is confirmed." : "Verification links are single-use and expire for your protection."}>
      {state === "loading" ? <AuthFlowStatus tone="info" title="Verification in progress">This usually takes only a moment.</AuthFlowStatus> : null}
      {state === "success" ? (
        <AuthFlowStatus tone="success" title="Verification complete">
          {updatedCurrentUser ? "Your signed-in account now shows as verified." : user ? "The email was verified. Your signed-in account belongs to a different user, so it was not changed." : "The email was verified. Log in to continue."}
        </AuthFlowStatus>
      ) : null}
      {state === "token-error" ? <AuthFlowStatus tone="error" title="Invalid, expired, or already used link">Request another verification email from the account page, or log in to continue.</AuthFlowStatus> : null}
      {state === "error" ? <ApiErrorStatus error={error} fallback="The email could not be verified." /> : null}
      <div className="flex flex-col gap-3 sm:flex-row">
        {user ? <Link href="/account" className="bg-ink-900 px-4 py-3 text-center text-sm font-bold text-white hover:bg-market-green">Go to account</Link> : null}
        <Link href="/login" className="border border-ink-300 px-4 py-3 text-center text-sm font-bold hover:border-ink-900">Log in</Link>
      </div>
    </AuthFlowShell>
  );
}
