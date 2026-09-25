import { readFile } from "node:fs/promises";
import test from "node:test";
import assert from "node:assert/strict";

const formSource = await readFile("apps/web/components/admin/admin-product-form.tsx", "utf8");
const headerSource = await readFile("apps/web/components/layout/site-header.tsx", "utf8");
const sellSource = await readFile("apps/web/components/auth/sell-form.tsx", "utf8");

test("admin product route source includes guest, non-admin, and admin form states", () => {
  assert.match(formSource, /Login required/);
  assert.match(formSource, /Admin required/);
  assert.match(formSource, /Product creation is admin-only/);
  assert.match(formSource, /Category/);
  assert.match(formSource, /Product name/);
  assert.match(formSource, /Price in USD/);
  assert.match(formSource, /Initial size/);
  assert.match(formSource, /Image URL/);
});

test("admin navigation is gated by is_admin", () => {
  assert.match(headerSource, /user\?\.is_admin/);
  assert.match(headerSource, /\/admin\/products\/new/);
});

test("seller form remains listing-only", () => {
  assert.match(sellSource, /Create a listing/);
  assert.doesNotMatch(sellSource, /Create Product/);
  assert.doesNotMatch(sellSource, /Image URL/);
});
