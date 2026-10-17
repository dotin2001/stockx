"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { Order } from "@/lib/types";
import { ErrorState, LoadingState } from "@/components/ui/states";
import { latestPaymentAttempt, OrderPaymentStatus } from "@/components/orders/order-payment-status";

const RETURN_POLL_INTERVAL_MS = 2000;
const RETURN_POLL_LIMIT = 10;

export function OrderDetailClient({ orderId }: { orderId: string }) {
  const { accessToken } = useAuth();
  const params = useSearchParams();
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState<"resume" | "cancel" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const returnedFromStripe = params.get("payment") === "return";
  const returnedFromCancelPage = params.get("payment") === "cancelled";

  const loadOrder = useCallback(async () => {
    if (!accessToken) return null;
    try {
      const value = await api.getOrder(accessToken, orderId);
      setOrder(value);
      setError(null);
      return value;
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not load this order.");
      return null;
    } finally {
      setLoading(false);
    }
  }, [accessToken, orderId]);

  useEffect(() => {
    void loadOrder();
  }, [loadOrder]);

  useEffect(() => {
    if (!returnedFromStripe || !accessToken) return;
    let active = true;
    let polls = 0;
    const timer = window.setInterval(() => {
      if (!active || polls >= RETURN_POLL_LIMIT) {
        window.clearInterval(timer);
        return;
      }
      polls += 1;
      void loadOrder().then((value) => {
        if (value && (value.payment_status === "paid" || value.status === "cancelled")) {
          window.clearInterval(timer);
        }
      });
    }, RETURN_POLL_INTERVAL_MS);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [accessToken, loadOrder, returnedFromStripe]);

  const attempt = useMemo(() => order ? latestPaymentAttempt(order) : null, [order]);
  const canResume = order?.status === "pending_payment" && attempt?.status === "open";
  const canCancel = order?.status === "pending_payment" && attempt != null && ["initializing", "open", "processing"].includes(attempt.status);

  async function resumePayment() {
    if (!accessToken || action) return;
    setAction("resume");
    setError(null);
    try {
      const session = await api.getPaymentSession(accessToken, orderId);
      if (!session.url) throw new Error("This payment session can no longer be resumed.");
      window.location.assign(session.url);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "This payment session can no longer be resumed.");
      setAction(null);
      await loadOrder();
    }
  }

  async function cancelPayment() {
    if (!accessToken || action) return;
    setAction("cancel");
    setError(null);
    try {
      await api.cancelPendingPayment(accessToken, orderId);
      await loadOrder();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not cancel this pending order.");
    } finally {
      setAction(null);
    }
  }

  if (loading) return <LoadingState label="Loading order..." />;
  if (!order) return <ErrorState title="Order not found" message={error ?? "This order is unavailable."} href="/orders" action="View order history" />;

  return (
    <section className="mx-auto grid max-w-5xl gap-6 lg:grid-cols-[1.25fr_0.75fr]">
      <div className="grid gap-5">
        <div className="surface p-6">
          {params.get("created") === "1" && order.status === "confirmed" ? <p className="text-sm font-bold uppercase tracking-wide text-market-green">Order confirmed</p> : null}
          {returnedFromStripe ? <p className="text-sm font-bold uppercase tracking-wide text-market-green">Returned from secure checkout</p> : null}
          {returnedFromCancelPage ? <p className="text-sm font-bold uppercase tracking-wide text-amber-700">You left Stripe Checkout</p> : null}
          <h1 className="mt-2 text-3xl font-black">{order.order_number}</h1>
          <p className="mt-2 text-sm text-ink-500">{order.confirmed_at ? `Confirmed ${new Date(order.confirmed_at).toLocaleString()}` : `Created ${new Date(order.created_at).toLocaleString()}`}</p>
          {returnedFromStripe && order.payment_status !== "paid" ? <p className="mt-4 text-sm text-ink-600">We are waiting for verified payment confirmation. This page refreshes briefly; the return URL itself does not prove payment.</p> : null}
          {returnedFromCancelPage && order.status === "pending_payment" ? <p className="mt-4 text-sm text-ink-600">Leaving Stripe did not cancel this reservation. Resume payment or explicitly cancel the pending order below.</p> : null}
          <div className="mt-4"><OrderPaymentStatus order={order} /></div>
          {error ? <p className="mt-4 border border-market-red/30 bg-red-50 px-3 py-2 text-sm font-semibold text-market-red">{error}</p> : null}
          {canResume || canCancel ? <div className="mt-4 flex flex-wrap gap-3">
            {canResume ? <button type="button" onClick={() => void resumePayment()} disabled={action !== null} className="bg-ink-900 px-4 py-3 text-sm font-bold text-white hover:bg-market-green disabled:opacity-50">{action === "resume" ? "Opening..." : "Resume Payment"}</button> : null}
            {canCancel ? <button type="button" onClick={() => void cancelPayment()} disabled={action !== null} className="border border-market-red px-4 py-3 text-sm font-bold text-market-red hover:bg-red-50 disabled:opacity-50">{action === "cancel" ? "Cancelling..." : "Cancel Pending Order"}</button> : null}
          </div> : null}
        </div>
        <div className="surface p-6"><h2 className="text-xl font-black">Items</h2><div className="mt-4 grid gap-4">{order.items.map((item) => <div key={item.id} className="border-b border-ink-200 pb-4"><div className="flex justify-between gap-4"><div><p className="font-bold">{item.product_name}</p><p className="mt-1 text-sm text-ink-500">{item.variant_label ?? "Standard"} · Qty {item.quantity}</p></div><p className="font-bold">{formatMoney(item.line_total_cents, order.currency)}</p></div></div>)}</div></div>
      </div>
      <aside className="grid h-fit gap-5">
        <div className="surface p-6"><h2 className="text-xl font-black">Shipping snapshot</h2><address className="mt-4 text-sm not-italic leading-6 text-ink-600"><strong className="text-ink-900">{order.shipping.recipient_name}</strong><br />{order.shipping.address_line1}<br />{order.shipping.address_line2 ? <>{order.shipping.address_line2}<br /></> : null}{order.shipping.city}{order.shipping.state ? `, ${order.shipping.state}` : ""} {order.shipping.postal_code}<br />{order.shipping.country}<br />{order.shipping.contact_email}<br />{order.shipping.contact_phone}</address></div>
        <div className="surface p-6"><h2 className="text-xl font-black">Totals</h2><dl className="mt-4 grid gap-2 text-sm"><Row label="Subtotal" value={formatMoney(order.subtotal_cents, order.currency)} /><Row label="Shipping" value={formatMoney(order.shipping_cents, order.currency)} /><Row label="Tax" value={formatMoney(order.tax_cents, order.currency)} /><Row label="Total" value={formatMoney(order.total_cents, order.currency)} strong /></dl></div>
      </aside>
    </section>
  );
}

function Row({ label, value, strong = false }: { label: string; value: string; strong?: boolean }) {
  return <div className={`flex justify-between gap-4 ${strong ? "border-t border-ink-900 pt-3 text-base font-black" : ""}`}><dt>{label}</dt><dd>{value}</dd></div>;
}
