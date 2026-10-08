"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { Order } from "@/lib/types";
import { ErrorState, LoadingState } from "@/components/ui/states";

export function OrderDetailClient({ orderId }: { orderId: string }) {
  const { accessToken } = useAuth();
  const params = useSearchParams();
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!accessToken) return;
    let active = true;
    api.getOrder(accessToken, orderId).then((value) => { if (active) setOrder(value); }).catch((caught) => { if (active) setError(caught instanceof ApiError ? caught.message : "Could not load this order."); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [accessToken, orderId]);
  if (loading) return <LoadingState label="Loading order..." />;
  if (error || !order) return <ErrorState title="Order not found" message={error ?? "This order is unavailable."} href="/orders" action="View order history" />;
  return (
    <section className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-[1.25fr_0.75fr]">
      <div className="grid gap-5">
        <div className="surface p-6">{params.get("created") === "1" ? <p className="text-sm font-bold uppercase tracking-wide text-market-green">Order confirmed</p> : null}<h1 className="mt-2 text-3xl font-black">{order.order_number}</h1><p className="mt-2 text-sm text-ink-500">Confirmed {new Date(order.confirmed_at ?? order.created_at).toLocaleString()}</p><p className="mt-4 border border-amber-300 bg-amber-50 px-4 py-3 text-sm font-bold text-amber-900">Payment status: Unpaid. No payment has been collected for this development order.</p></div>
        <div className="surface p-6"><h2 className="text-xl font-black">Items</h2><div className="mt-4 grid gap-4">{order.items.map((item) => <div key={item.id} className="border-b border-ink-200 pb-4"><div className="flex justify-between gap-4"><div><p className="font-bold">{item.product_name}</p><p className="mt-1 text-sm text-ink-500">{item.variant_label ?? "Standard"} · Qty {item.quantity}</p></div><p className="font-bold">{formatMoney(item.line_total_cents, order.currency)}</p></div></div>)}</div></div>
      </div>
      <aside className="grid h-fit gap-5">
        <div className="surface p-6"><h2 className="text-xl font-black">Shipping snapshot</h2><address className="mt-4 text-sm not-italic leading-6 text-ink-600"><strong className="text-ink-900">{order.shipping.recipient_name}</strong><br />{order.shipping.address_line1}<br />{order.shipping.address_line2 ? <>{order.shipping.address_line2}<br /></> : null}{order.shipping.city}{order.shipping.state ? `, ${order.shipping.state}` : ""} {order.shipping.postal_code}<br />{order.shipping.country}<br />{order.shipping.contact_email}<br />{order.shipping.contact_phone}</address></div>
        <div className="surface p-6"><h2 className="text-xl font-black">Totals</h2><dl className="mt-4 grid gap-2 text-sm"><Row label="Subtotal" value={formatMoney(order.subtotal_cents, order.currency)} /><Row label="Shipping" value={formatMoney(order.shipping_cents, order.currency)} /><Row label="Tax" value={formatMoney(order.tax_cents, order.currency)} /><Row label="Total" value={formatMoney(order.total_cents, order.currency)} strong /></dl></div>
      </aside>
    </section>
  );
}

function Row({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) { return <div className={`flex justify-between gap-4 ${strong ? "border-t border-ink-900 pt-3 text-base font-black" : ""}`}><dt>{label}</dt><dd>{value}</dd></div>; }
