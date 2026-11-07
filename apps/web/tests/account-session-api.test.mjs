import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import { loadTypescriptModule } from "./helpers/load-typescript.mjs";

const apiModule = loadTypescriptModule(new URL("../lib/api.ts", import.meta.url));
const sessionModule = loadTypescriptModule(new URL("../lib/auth-session.ts", import.meta.url));
const returnUrlModule = loadTypescriptModule(new URL("../lib/return-url.ts", import.meta.url));
const authFlowModule = loadTypescriptModule(new URL("../lib/auth-flow.ts", import.meta.url));
const { api, ApiError, setAuthSessionAdapter } = apiModule;
const { createAuthSessionCoordinator } = sessionModule;
const { normalizeInternalReturnUrl, safeInternalReturnUrl } = returnUrlModule;

afterEach(() => {
  setAuthSessionAdapter(null);
  delete globalThis.fetch;
});

function jsonResponse(status, body, headers) {
  return new Response(status === 204 ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers }
  });
}

test("account action API methods use confirmed paths, payloads, credentials, and response shapes", async () => {
  const requests = [];
  globalThis.fetch = async (url, options) => {
    requests.push({ url, options, body: options.body ? JSON.parse(options.body) : null });
    if (url.endsWith("/logout-all")) return jsonResponse(204);
    if (url.endsWith("/confirm")) return jsonResponse(200, { id: "user-1", is_verified: true });
    return jsonResponse(202, { message: "If the account is eligible, instructions will be sent." });
  };

  const accepted = await api.requestPasswordReset({ email: "person@example.com" });
  const resetUser = await api.confirmPasswordReset({ token: "t".repeat(32), new_password: "password123" });
  await api.requestVerification({ email: "person@example.com" });
  const verifiedUser = await api.confirmVerification({ token: "v".repeat(32) });
  await api.logoutAll("access-token");

  assert.equal(accepted.message, "If the account is eligible, instructions will be sent.");
  assert.equal(resetUser.id, "user-1");
  assert.equal(verifiedUser.is_verified, true);
  assert.deepEqual(requests.map(({ url }) => new URL(url).pathname), [
    "/api/v1/auth/password-reset/request",
    "/api/v1/auth/password-reset/confirm",
    "/api/v1/auth/verification/request",
    "/api/v1/auth/verification/confirm",
    "/api/v1/auth/logout-all"
  ]);
  assert.ok(requests.every(({ options }) => options.method === "POST"));
  assert.ok(requests.every(({ options }) => options.credentials === "include"));
  assert.equal(requests.at(-1).options.headers.get("Authorization"), "Bearer access-token");
});

test("ApiError preserves normalized codes, details, status, Retry-After, and presentation kind", async () => {
  const cases = [
    [422, "validation_error", "validation"],
    [400, "invalid_action_token", "invalid-action-token"],
    [429, "rate_limited", "rate-limited"],
    [401, "not_authenticated", "unauthorized"],
    [403, "forbidden", "access-denied"],
    [500, "api_error", "api-error"]
  ];

  for (const [status, code, kind] of cases) {
    globalThis.fetch = async () => jsonResponse(status, {
      error: { code, message: `${kind} message`, details: { field: "email" } }
    }, status === 429 ? { "Retry-After": "17" } : undefined);
    await assert.rejects(api.requestPasswordReset({ email: "person@example.com" }), (error) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.status, status);
      assert.equal(error.code, code);
      assert.deepEqual(error.details, { field: "email" });
      assert.equal(error.kind, kind);
      assert.equal(error.retryAfterSeconds, status === 429 ? 17 : null);
      return true;
    });
  }
});

test("return URL normalization accepts internal path/query/hash and rejects redirect traps", () => {
  const origin = "https://market.example";
  assert.equal(normalizeInternalReturnUrl("/account?tab=security#sessions", origin), "/account?tab=security#sessions");
  assert.equal(normalizeInternalReturnUrl("/orders/abc", origin), "/orders/abc");
  for (const unsafe of [
    "https://evil.example/account",
    "//evil.example/account",
    "/\\evil.example/account",
    "account",
    "/login",
    "/signup?redirect=/account",
    "/forgot-password",
    "/reset-password?token=secret",
    "/verify-email?token=secret",
    "/account\nnext"
  ]) {
    assert.equal(normalizeInternalReturnUrl(unsafe, origin), null, unsafe);
  }
  assert.equal(safeInternalReturnUrl("//evil.example", "/account"), "/account");
});

test("client validation matches confirmed email and password bounds", () => {
  assert.equal(authFlowModule.isValidEmail("person@example.com"), true);
  assert.equal(authFlowModule.isValidEmail("not-an-email"), false);
  assert.match(authFlowModule.passwordValidationMessage("short"), /at least 8/);
  assert.match(authFlowModule.passwordValidationMessage("x".repeat(129)), /no more than 128/);
  assert.equal(authFlowModule.passwordValidationMessage("password123"), null);
});

test("session coordinator is single-flight and ignores a stale refresh after logout generation changes", async () => {
  let resolveRefresh;
  let refreshCount = 0;
  let applyCount = 0;
  let generation = 4;
  const coordinator = createAuthSessionCoordinator({
    snapshot: () => ({ accessToken: "old", generation }),
    requestRefresh: () => {
      refreshCount += 1;
      return new Promise((resolve) => { resolveRefresh = resolve; });
    },
    apply: (_response, expected) => {
      if (generation !== expected) return false;
      applyCount += 1;
      generation += 1;
      return true;
    },
    terminate: () => {}
  });

  const first = coordinator.refresh(4);
  const second = coordinator.refresh(4);
  assert.equal(first, second);
  assert.equal(refreshCount, 1);
  generation += 1;
  resolveRefresh({ access_token: "new", token_type: "bearer", user: { id: "user-1" } });
  assert.equal(await first, null);
  assert.equal(await second, null);
  assert.equal(applyCount, 0);
});

function coordinatedAdapter({ rejectRefresh = false } = {}) {
  let session = { accessToken: "old-token", generation: 1 };
  let refreshCount = 0;
  let terminateCount = 0;
  let releaseRefresh;
  const refreshGate = new Promise((resolve, reject) => { releaseRefresh = rejectRefresh ? () => reject(new Error("refresh failed")) : resolve; });
  const adapter = createAuthSessionCoordinator({
    snapshot: () => session,
    requestRefresh: () => { refreshCount += 1; return refreshGate; },
    apply: (response, expected) => {
      if (session.generation !== expected) return false;
      session = { accessToken: response.access_token, generation: expected + 1 };
      return true;
    },
    terminate: (expected) => {
      if (session.generation !== expected) return;
      terminateCount += 1;
      session = { accessToken: null, generation: expected + 1 };
    }
  });
  return { adapter, releaseRefresh, counts: () => ({ refreshCount, terminateCount }) };
}

test("concurrent access-token 401s share one refresh and retry each request once", async () => {
  const recovery = coordinatedAdapter();
  setAuthSessionAdapter(recovery.adapter);
  let requestCount = 0;
  globalThis.fetch = async (_url, options) => {
    requestCount += 1;
    return options.headers.get("Authorization") === "Bearer old-token"
      ? jsonResponse(401, { error: { code: "invalid_access_token", message: "Expired" } })
      : jsonResponse(200, []);
  };

  const first = api.listWatchlist("old-token");
  const second = api.listWatchlist("old-token");
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(recovery.counts().refreshCount, 1);
  recovery.releaseRefresh({ access_token: "new-token", token_type: "bearer", user: { id: "user-1" } });
  assert.deepEqual(await first, []);
  assert.deepEqual(await second, []);
  assert.equal(requestCount, 4);
  assert.equal(recovery.counts().terminateCount, 0);
});

test("failed refresh and a second 401 terminate recovery without a refresh loop", async () => {
  const failed = coordinatedAdapter({ rejectRefresh: true });
  setAuthSessionAdapter(failed.adapter);
  globalThis.fetch = async () => jsonResponse(401, { error: { code: "invalid_access_token", message: "Expired" } });
  const request = api.getCart("old-token");
  await new Promise((resolve) => setImmediate(resolve));
  failed.releaseRefresh();
  await assert.rejects(request, (error) => error instanceof ApiError && error.status === 401);
  assert.deepEqual(failed.counts(), { refreshCount: 1, terminateCount: 1 });

  const second401 = coordinatedAdapter();
  setAuthSessionAdapter(second401.adapter);
  let calls = 0;
  globalThis.fetch = async () => { calls += 1; return jsonResponse(401, { error: { code: "invalid_access_token", message: "Expired" } }); };
  const retried = api.getCart("old-token");
  await new Promise((resolve) => setImmediate(resolve));
  second401.releaseRefresh({ access_token: "new-token", token_type: "bearer", user: { id: "user-1" } });
  await assert.rejects(retried, (error) => error instanceof ApiError && error.status === 401);
  assert.equal(calls, 2);
  assert.deepEqual(second401.counts(), { refreshCount: 1, terminateCount: 1 });
});

test("public 401 and authenticated 403 never invoke refresh", async () => {
  const recovery = coordinatedAdapter();
  setAuthSessionAdapter(recovery.adapter);
  globalThis.fetch = async (url) => url.includes("/products?")
    ? jsonResponse(401, { error: { code: "unauthorized", message: "Unauthorized" } })
    : jsonResponse(403, { error: { code: "forbidden", message: "Forbidden" } });

  await assert.rejects(api.listProducts(), (error) => error instanceof ApiError && error.status === 401);
  await assert.rejects(api.listWatchlist("old-token"), (error) => error instanceof ApiError && error.kind === "access-denied");
  assert.equal(recovery.counts().refreshCount, 0);
});
