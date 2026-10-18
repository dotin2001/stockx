import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

function source(path) {
  return readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
}

test("admin order API contracts are typed, authenticated, and encode only supplied filters", () => {
  const api = source("lib/api.ts");
  const types = source("lib/types.ts");
  assert.match(types, /export type AdminOrderSummary/);
  assert.match(types, /latest_payment_attempt: PaymentAttempt \| null/);
  assert.match(types, /export type AdminOrderQuery/);
  assert.match(api, /if \(query\.search !== undefined\) params\.set\("search", query\.search\)/);
  assert.match(api, /if \(query\.payment_status !== undefined\) params\.set\("payment_status", query\.payment_status\)/);
  assert.match(api, /apiRequest<AdminOrderPage>\(`\/api\/v1\/admin\/orders/);
  assert.match(api, /apiRequest<Order>\(`\/api\/v1\/admin\/orders\/\$\{encodeURIComponent\(orderId\)\}`/);
  assert.match(api, /accessToken/);
});

test("payment presentation accepts the minimal safe state for customer and admin orders", () => {
  const payment = source("components/orders/order-payment-status.tsx");
  assert.match(payment, /export type OrderPaymentState/);
  assert.match(payment, /latest_payment_attempt: PaymentAttempt \| null/);
  assert.match(payment, /export function getPaymentPresentation/);
  assert.match(payment, /Payment status unavailable/);
  for (const state of ["processing", "initializing", "open", "paid", "failed", "expired", "cancelled"]) {
    assert.match(payment, new RegExp(`\\"${state}\\"`));
  }
  assert.doesNotMatch(payment, /provider_session_id|hosted_url|idempotency_key/);
});

test("admin order list is URL-backed, filtered, paginated, responsive, and role gated", () => {
  const list = source("components/admin/admin-orders-panel.tsx");
  const page = source("app/admin/orders/page.tsx");
  assert.match(page, /AdminOrdersPanel/);
  assert.match(list, /user\?\.is_admin \|\| user\?\.is_supreme_admin/);
  assert.match(list, /useSearchParams/);
  assert.match(list, /searchParams\.get\("status"\)/);
  assert.match(list, /searchParams\.get\("payment_status"\)/);
  assert.match(list, /next\.delete\("offset"\)/);
  assert.match(list, /listAdminOrders\(accessToken, query\)/);
  assert.match(list, /lg:grid-cols/);
  assert.match(list, /No orders found/);
  assert.match(list, /Refreshing orders/);
  assert.match(list, /Previous/);
  assert.match(list, /Next/);
});

test("admin order detail is a safe immutable review and preserves list return state", () => {
  const detail = source("components/admin/admin-order-detail-panel.tsx");
  const page = source("app/admin/orders/[id]/page.tsx");
  assert.match(page, /AdminOrderDetailPanel/);
  assert.match(detail, /getAdminOrder\(accessToken, orderId\)/);
  assert.match(detail, /safeReturnPath/);
  assert.match(detail, /Customer snapshot/);
  assert.match(detail, /Items snapshot/);
  assert.match(detail, /Shipping snapshot/);
  assert.match(detail, /Payment attempts/);
  assert.match(detail, /Reservation expires/);
  assert.match(detail, /Inventory released/);
  for (const forbidden of ["Resume Payment", "Cancel Pending Order", "Refund", "Fulfill", "Ship order", "Update status"]) {
    assert.doesNotMatch(detail, new RegExp(forbidden, "i"));
  }
});

test("admin orders navigation is present on desktop and mobile within the admin role gate", () => {
  const header = source("components/layout/site-header.tsx");
  assert.equal((header.match(/href="\/admin\/orders"/g) ?? []).length, 2);
  assert.match(header, /user\.is_admin \|\| user\.is_supreme_admin/);
  assert.match(header, /user\?\.is_admin \|\| user\?\.is_supreme_admin/);
});
