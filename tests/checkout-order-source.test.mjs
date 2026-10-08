import { readFile } from "node:fs/promises";
import test from "node:test";
import assert from "node:assert/strict";

const checkout = await readFile("apps/web/components/checkout/checkout-page-client.tsx", "utf8");
const history = await readFile("apps/web/components/orders/order-history-client.tsx", "utf8");
const detail = await readFile("apps/web/components/orders/order-detail-client.tsx", "utf8");
const cart = await readFile("apps/web/components/cart/cart-page-client.tsx", "utf8");
const account = await readFile("apps/web/components/auth/account-dashboard.tsx", "utf8");
const product = await readFile("apps/web/components/catalog/product-detail-view.tsx", "utf8");
const api = await readFile("apps/web/lib/api.ts", "utf8");

test("checkout uses server summary, stable idempotency, disabled messaging, and stale refresh", () => {
  assert.match(checkout, /api\.getCheckoutSummary/);
  assert.match(checkout, /useRef\(newAttemptKey\(\)\)/);
  assert.match(checkout, /Idempotency|attemptKey/);
  assert.match(checkout, /order_placement_enabled/);
  assert.match(checkout, /Refresh summary/);
  assert.match(checkout, /unpaid order/);
  assert.match(api, /"Idempotency-Key"/);
});

test("order history and detail expose read-only confirmed unpaid snapshots", () => {
  assert.match(history, /api\.listOrders/);
  assert.match(history, /Previous/);
  assert.match(history, /Next/);
  assert.match(history, /No orders yet/);
  assert.match(detail, /api\.getOrder/);
  assert.match(detail, /Payment status: Unpaid/);
  assert.match(detail, /Shipping snapshot/);
  assert.doesNotMatch(detail, /Pay now|Cancel order|Refund|Ship order/);
});

test("cart and account navigate to dedicated checkout and order history", () => {
  assert.match(cart, /encodeURIComponent\("\/checkout"\)/);
  assert.match(cart, /router\.push\("\/checkout"\)/);
  assert.match(account, /href="\/checkout"/);
  assert.match(account, /href="\/orders"/);
  assert.match(product, /router\.push\("\/checkout"\)/);
  assert.doesNotMatch(product, /\/account\?checkout=1/);
  assert.doesNotMatch(account, /Checkout is not available yet/);
});
