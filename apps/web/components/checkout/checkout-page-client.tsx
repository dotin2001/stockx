"use client";

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { CheckoutSummary, ShippingAddress } from "@/lib/types";
import { ErrorState, LoadingState } from "@/components/ui/states";

function newAttemptKey() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `checkout-${Date.now()}-${Math.random()}`;
}

export function CheckoutPageClient() {
  const router = useRouter();
  const { accessToken } = useAuth();
  const [summary, setSummary] = useState<CheckoutSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stale, setStale] = useState(false);
  const attemptKey = useRef(newAttemptKey());

  const loadSummary = useCallback(async () => {
    if (!accessToken) return;
    setLoading(true);
    try {
      setSummary(await api.getCheckoutSummary(accessToken));
      setError(null);
      setStale(false);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not load checkout.");
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    void loadSummary();
  }, [loadSummary]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken || !summary || !summary.order_placement_enabled) return;
    const form = new FormData(event.currentTarget);
    const shipping: ShippingAddress = {
      recipient_name: String(form.get("recipient_name") ?? ""),
      contact_email: String(form.get("contact_email") ?? ""),
      contact_phone: String(form.get("contact_phone") ?? ""),
      address_line1: String(form.get("address_line1") ?? ""),
      address_line2: String(form.get("address_line2") ?? "") || null,
      city: String(form.get("city") ?? ""),
      state: String(form.get("state") ?? "") || null,
      postal_code: String(form.get("postal_code") ?? ""),
      country: String(form.get("country") ?? "").toUpperCase()
    };
    setSubmitting(true);
    setError(null);
    try {
      const order = await api.createOrder(accessToken, attemptKey.current, { checkout_token: summary.checkout_token, shipping });
      router.push(`/orders/${order.id}?created=1`);
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "checkout_changed") {
        setStale(true);
        setError("Your cart or inventory changed. Refresh the checkout summary before confirming.");
      } else {
        setError(caught instanceof ApiError ? caught.message : "Could not confirm this order.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <LoadingState label="Loading checkout..." />;
  if (!summary) return <ErrorState title="Checkout unavailable" message={error ?? undefined} href="/cart" action="Return to cart" />;

  return (
    <form onSubmit={submit} className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-[1.3fr_0.7fr]">
      <section className="surface grid gap-5 p-6">
        <div>
          <p className="text-sm font-bold uppercase tracking-wide text-market-green">Checkout</p>
          <h1 className="mt-2 text-3xl font-black">Shipping details</h1>
          <p className="mt-2 text-sm text-ink-500">This development checkout records an unpaid order. It does not collect payment.</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field name="recipient_name" label="Recipient name" autoComplete="name" />
          <Field name="contact_email" label="Contact email" type="email" autoComplete="email" />
          <Field name="contact_phone" label="Contact phone" type="tel" autoComplete="tel" />
          <Field name="address_line1" label="Address line 1" autoComplete="address-line1" />
          <Field name="address_line2" label="Address line 2" required={false} autoComplete="address-line2" />
          <Field name="city" label="City" autoComplete="address-level2" />
          <Field name="state" label="State / region" required={false} autoComplete="address-level1" />
          <Field name="postal_code" label="Postal code" autoComplete="postal-code" />
          <Field name="country" label="Country code" minLength={2} maxLength={2} placeholder="US" autoComplete="country" />
        </div>
        {error ? <p className="border border-market-red/30 bg-red-50 px-3 py-2 text-sm font-semibold text-market-red">{error}</p> : null}
        {stale ? <button type="button" onClick={() => void loadSummary()} className="border border-ink-900 px-4 py-3 text-sm font-bold hover:bg-ink-900 hover:text-white">Refresh summary</button> : null}
        {!summary.order_placement_enabled ? (
          <p className="border border-ink-200 bg-ink-50 px-4 py-3 text-sm font-semibold text-ink-700">Order placement is disabled. A developer can explicitly enable manual checkout for local testing.</p>
        ) : (
          <p className="border border-market-green/30 bg-market-mint px-4 py-3 text-sm font-semibold text-ink-800">Manual development checkout is enabled. Orders are confirmed but remain unpaid.</p>
        )}
      </section>
      <aside className="surface h-fit p-6">
        <h2 className="text-xl font-black">Order summary</h2>
        <div className="mt-4 grid gap-4">
          {summary.items.map((item) => (
            <div key={item.cart_item_id} className="border-b border-ink-200 pb-4 text-sm">
              <Link href={`/product/${item.product_slug}`} className="font-bold hover:text-market-green">{item.product_name}</Link>
              <p className="mt-1 text-ink-500">{item.variant_label ? `${item.variant_label} · ` : ""}Qty {item.quantity}</p>
              <p className="mt-1 font-semibold">{formatMoney(item.line_total_cents, summary.currency)}</p>
            </div>
          ))}
        </div>
        <dl className="mt-5 grid gap-2 text-sm">
          <Total label="Subtotal" value={formatMoney(summary.subtotal_cents, summary.currency)} />
          <Total label="Shipping" value={formatMoney(summary.shipping_cents, summary.currency)} />
          <Total label="Tax" value={formatMoney(summary.tax_cents, summary.currency)} />
          <Total label="Total" value={formatMoney(summary.total_cents, summary.currency)} strong />
        </dl>
        <button type="submit" disabled={!summary.order_placement_enabled || submitting || stale} className="mt-6 w-full bg-ink-900 px-4 py-3 text-sm font-bold text-white hover:bg-market-green disabled:cursor-not-allowed disabled:opacity-50">
          {submitting ? "Confirming..." : "Confirm unpaid order"}
        </button>
      </aside>
    </form>
  );
}

function Field({ label, required = true, ...props }: { label: string; required?: boolean } & React.InputHTMLAttributes<HTMLInputElement>) {
  return <label className="grid gap-2 text-sm font-semibold">{label}<input {...props} required={required} className="border border-ink-200 px-3 py-3 font-normal" /></label>;
}

function Total({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return <div className={`flex justify-between gap-4 ${strong ? "border-t border-ink-900 pt-3 text-base font-black" : ""}`}><dt>{label}</dt><dd>{value}</dd></div>;
}
