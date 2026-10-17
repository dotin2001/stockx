import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

function source(path) {
  return readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
}

test("Stripe session calls are authenticated and idempotent", () => {
  const api = source("lib/api.ts");
  assert.match(api, /createCheckoutSession: \(accessToken: string, idempotencyKey: string/);
  assert.match(api, /apiRequest<PaymentSession>\("\/api\/v1\/checkout\/sessions"/);
  assert.match(api, /headers: \{ "Idempotency-Key": idempotencyKey \}/);
  assert.match(api, /getPaymentSession: \(accessToken: string, orderId: UUID\)/);
  assert.match(api, /cancelPendingPayment: \(accessToken: string, orderId: UUID\)/);
});

test("checkout redirects only from the returned hosted session and guards duplicate submit", () => {
  const checkout = source("components/checkout/checkout-page-client.tsx");
  assert.match(checkout, /summary\.checkout_mode === "stripe"/);
  assert.match(checkout, /if \(!accessToken \|\| !summary \|\| !summary\.order_placement_enabled \|\| submitting\) return/);
  assert.match(checkout, /window\.location\.assign\(session\.url\)/);
  assert.match(checkout, /Continue to secure payment/);
});

test("order return messaging depends on authenticated order state", () => {
  const detail = source("components/orders/order-detail-client.tsx");
  assert.match(detail, /api\.getOrder\(accessToken, orderId\)/);
  assert.match(detail, /order\.payment_status !== "paid"/);
  assert.match(detail, /return URL itself does not prove payment/);
  assert.match(detail, /RETURN_POLL_LIMIT = 10/);
  assert.match(detail, /Resume Payment/);
  assert.match(detail, /Cancel Pending Order/);
});
