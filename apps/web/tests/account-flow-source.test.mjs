import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

function source(path) {
  return readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
}

test("password recovery routes expose validation, neutral success, pending, cooldown, and token failure states", () => {
  const forgot = source("components/auth/forgot-password-form.tsx");
  const reset = source("components/auth/reset-password-form.tsx");
  const login = source("components/auth/auth-form.tsx");
  assert.match(login, /href="\/forgot-password"/);
  assert.match(forgot, /isValidEmail/);
  assert.match(forgot, /If the account is eligible/);
  assert.match(forgot, /aria-busy=\{submitting\}/);
  assert.match(forgot, /retryAfterSeconds/);
  assert.match(reset, /passwordValidationMessage/);
  assert.match(reset, /passwords must match/i);
  assert.match(reset, /invalid-action-token/);
  assert.match(reset, /invalid, expired, or already used/i);
  assert.match(reset, /Request a new reset/);
  assert.doesNotMatch(reset, /localStorage|sessionStorage|console\./);
});

test("verification deduplicates per token and updates only a matching authenticated identity", () => {
  const verify = source("components/auth/verify-email-panel.tsx");
  const context = source("contexts/auth-context.tsx");
  assert.match(verify, /confirmationByToken = new Map/);
  assert.match(verify, /confirmVerificationOnce/);
  assert.match(verify, /updateUserIfMatches\(confirmedUser\)/);
  assert.match(context, /sessionRef\.current\.user\.id !== updatedUser\.id/);
  assert.match(verify, /different user/);
  assert.match(verify, /Invalid, expired, or already used link/);
});

test("account security controls show server verification state and require explicit logout-all confirmation", () => {
  const account = source("components/auth/account-security-panel.tsx");
  assert.match(account, /user\.is_verified/);
  assert.match(account, /retryAfterSeconds/);
  assert.match(account, /aria-busy=\{resending\}/);
  assert.match(account, /Are you sure you want to log out every device/);
  assert.match(account, />Cancel</);
  assert.match(account, /await logoutAll\(\)/);
  assert.match(account, /setLogoutError\(error\)/);
});

test("shared auth flow presentation provides live regions, focus visibility, and narrow-screen layouts", () => {
  const status = source("components/auth/auth-flow-status.tsx");
  const shell = source("components/auth/auth-flow-shell.tsx");
  const globals = source("app/globals.css");
  assert.match(status, /role=\{tone === "error" \? "alert" : "status"\}/);
  assert.match(status, /aria-live/);
  assert.match(shell, /max-w-lg/);
  assert.match(shell, /p-5 sm:p-8/);
  assert.match(globals, /focus-visible:outline/);
  for (const file of ["forgot-password-form.tsx", "reset-password-form.tsx", "account-security-panel.tsx"]) {
    const component = source(`components/auth/${file}`);
    assert.match(component, /disabled=/);
  }
  assert.match(source("components/auth/account-security-panel.tsx"), /sm:flex-row/);
  assert.match(source("components/auth/reset-password-form.tsx"), /sm:flex-row/);
});
