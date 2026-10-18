"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { Order } from "@/lib/types";
import { getOrderPaymentPresentation, OrderPaymentStatus } from "@/components/orders/order-payment-status";
import { ErrorState, LoadingState } from "@/components/ui/states";

function safeReturnPath(value: string | null) {
  return value === "/admin/orders" || value?.startsWith("/admin/orders?") ? value : "/admin/orders";
}

function DateValue({ value }: { value: string | null }) {
  return <>{value ? new Date(value).toLocaleString() : "—"}</>;
}

function MoneyRow({ label, value, currency, strong = false }: { label: string; value: number; currency: string; strong?: boolean }) {
  return <div className={`flex justify-between gap-4 ${strong ? "border-t border-ink-900 pt-3 text-base font-black" : ""}`}><dt>{label}</dt><dd>{formatMoney(value, currency)}</dd></div>;
}

export function AdminOrderDetailPanel({ orderId }: { orderId: string }) {
  const { status: authStatus, user, accessToken } = useAuth();
  const searchParams = useSearchParams();
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isAdmin = Boolean(user?.is_admin || user?.is_supreme_admin);
  const returnPath = safeReturnPath(searchParams.get("return_to"));

  useEffect(() => {
    if (authStatus === "checking") return;
    if (authStatus !== "authenticated" || !isAdmin || !accessToken) {
      setLoading(false);
      return;
    }
    let active = true;
    setLoading(true);
    api
      .getAdminOrder(accessToken, orderId)
      .then((value) => {
        if (active) {
          setOrder(value);
          setError(null);
        }
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof ApiError ? caught.message : "Could not load this order.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [accessToken, authStatus, isAdmin, orderId]);

  const paymentPresentation = useMemo(() => order ? getOrderPaymentPresentation(order) : null, [order]);

  if (authStatus === "checking" || loading) return <LoadingState label="Loading order review..." />;
  if (authStatus !== "authenticated") {
    return <ErrorState title="Login required" message="Sign in with an admin account to review this order." href={`/login?next=/admin/orders/${orderId}`} action="Login" />;
  }
  if (!isAdmin) {
    return <ErrorState title="Admin required" message="Order review is only available to store admins." href="/account" action="Return to account" />;
  }
  if (!order) {
    return <ErrorState title="Order not found" message={error ?? "This order is unavailable."} href={returnPath} action="Return to orders" />;
  }

  return (
    <section className="grid gap-5">
      <div className="surface p-5 sm:p-6">
        <Link href={returnPath} className="text-sm font-black text-market-green hover:text-ink-900">← Back to orders</Link>
        <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-bold uppercase tracking-wide text-market-green">Read-only order review</p>
            <h1 className="mt-2 text-3xl font-black">{order.order_number}</h1>
            <p className="mt-2 text-sm text-ink-500">Created {new Date(order.created_at).toLocaleString()}</p>
          </div>
          <span className="border border-ink-200 bg-ink-50 px-3 py-2 text-xs font-black uppercase text-ink-700">{order.status.replaceAll("_", " ")}</span>
        </div>
        <div className="mt-5"><OrderPaymentStatus order={order} /></div>
        {paymentPresentation ? <p className="sr-only">{paymentPresentation.title}</p> : null}
      </div>

      <div className="grid gap-5 lg:grid-cols-[1.25fr_0.75fr]">
        <div className="grid gap-5">
          <div className="surface p-5 sm:p-6">
            <h2 className="text-xl font-black">Items snapshot</h2>
            <div className="mt-4 grid gap-4">
              {order.items.map((item) => (
                <article key={item.id} className="border-b border-ink-200 pb-4 last:border-0 last:pb-0">
                  <div className="flex justify-between gap-4">
                    <div>
                      <p className="font-bold">{item.product_name}</p>
                      <p className="mt-1 text-sm text-ink-500">{item.variant_label ?? "Standard"} · Qty {item.quantity}</p>
                      {item.variant_sku ? <p className="mt-1 text-xs font-semibold text-ink-400">SKU {item.variant_sku}</p> : null}
                    </div>
                    <p className="font-bold">{formatMoney(item.line_total_cents, order.currency)}</p>
                  </div>
                </article>
              ))}
            </div>
          </div>

          <div className="surface p-5 sm:p-6">
            <h2 className="text-xl font-black">Payment attempts</h2>
            {order.payment_attempts.length === 0 ? (
              <p className="mt-4 text-sm text-ink-500">No online payment attempts. This may be a manual order.</p>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[38rem] text-left text-sm">
                  <thead className="border-b border-ink-300 text-xs uppercase text-ink-500"><tr><th className="pb-3 pr-4">Status</th><th className="pb-3 pr-4">Amount</th><th className="pb-3 pr-4">Expires</th><th className="pb-3">Completed</th></tr></thead>
                  <tbody>
                    {order.payment_attempts.map((attempt) => (
                      <tr key={attempt.id} className="border-b border-ink-100 last:border-0">
                        <td className="py-3 pr-4 font-bold capitalize">{attempt.status}</td>
                        <td className="py-3 pr-4">{formatMoney(attempt.amount_cents, attempt.currency)}</td>
                        <td className="py-3 pr-4"><DateValue value={attempt.expires_at} /></td>
                        <td className="py-3"><DateValue value={attempt.completed_at} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        <aside className="grid h-fit gap-5">
          <div className="surface p-5 sm:p-6">
            <h2 className="text-xl font-black">Customer snapshot</h2>
            <p className="mt-4 font-bold">{order.customer_name}</p>
            <p className="mt-1 break-all text-sm text-ink-500">{order.customer_email}</p>
          </div>
          <div className="surface p-5 sm:p-6">
            <h2 className="text-xl font-black">Shipping snapshot</h2>
            <address className="mt-4 text-sm not-italic leading-6 text-ink-600">
              <strong className="text-ink-900">{order.shipping.recipient_name}</strong><br />
              {order.shipping.address_line1}<br />
              {order.shipping.address_line2 ? <>{order.shipping.address_line2}<br /></> : null}
              {order.shipping.city}{order.shipping.state ? `, ${order.shipping.state}` : ""} {order.shipping.postal_code}<br />
              {order.shipping.country}<br />
              {order.shipping.contact_email}<br />
              {order.shipping.contact_phone}
            </address>
          </div>
          <div className="surface p-5 sm:p-6">
            <h2 className="text-xl font-black">Totals</h2>
            <dl className="mt-4 grid gap-2 text-sm">
              <MoneyRow label="Subtotal" value={order.subtotal_cents} currency={order.currency} />
              <MoneyRow label="Shipping" value={order.shipping_cents} currency={order.currency} />
              <MoneyRow label="Tax" value={order.tax_cents} currency={order.currency} />
              <MoneyRow label="Total" value={order.total_cents} currency={order.currency} strong />
            </dl>
          </div>
          <div className="surface p-5 sm:p-6">
            <h2 className="text-xl font-black">Lifecycle</h2>
            <dl className="mt-4 grid gap-3 text-sm">
              <div><dt className="font-bold text-ink-500">Created</dt><dd className="mt-1"><DateValue value={order.created_at} /></dd></div>
              <div><dt className="font-bold text-ink-500">Confirmed</dt><dd className="mt-1"><DateValue value={order.confirmed_at} /></dd></div>
              <div><dt className="font-bold text-ink-500">Reservation expires</dt><dd className="mt-1"><DateValue value={order.reservation_expires_at} /></dd></div>
              <div><dt className="font-bold text-ink-500">Inventory released</dt><dd className="mt-1"><DateValue value={order.inventory_released_at} /></dd></div>
              <div><dt className="font-bold text-ink-500">Last updated</dt><dd className="mt-1"><DateValue value={order.updated_at} /></dd></div>
            </dl>
          </div>
        </aside>
      </div>
    </section>
  );
}
