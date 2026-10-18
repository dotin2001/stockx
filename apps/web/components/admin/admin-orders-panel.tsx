"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import { formatCount, formatMoney } from "@/lib/format";
import type { AdminOrderPage, AdminOrderQuery, OrderStatus, PaymentStatus } from "@/lib/types";
import { getPaymentPresentation, PaymentStatusPresentation } from "@/components/orders/order-payment-status";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";

const PAGE_SIZE = 20;
const ORDER_STATUSES: OrderStatus[] = ["pending_payment", "confirmed", "cancelled"];
const PAYMENT_STATUSES: PaymentStatus[] = ["unpaid", "paid", "failed", "refunded"];

function readOffset(value: string | null): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : 0;
}

function readOrderStatus(value: string | null): OrderStatus | undefined {
  return ORDER_STATUSES.includes(value as OrderStatus) ? (value as OrderStatus) : undefined;
}

function readPaymentStatus(value: string | null): PaymentStatus | undefined {
  return PAYMENT_STATUSES.includes(value as PaymentStatus) ? (value as PaymentStatus) : undefined;
}

function titleCaseStatus(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function AdminOrdersPanel() {
  const { status: authStatus, user, accessToken } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const queryString = searchParams.toString();
  const search = searchParams.get("search")?.trim() ?? "";
  const orderStatus = readOrderStatus(searchParams.get("status"));
  const paymentStatus = readPaymentStatus(searchParams.get("payment_status"));
  const offset = readOffset(searchParams.get("offset"));
  const [searchDraft, setSearchDraft] = useState(search);
  const [page, setPage] = useState<AdminOrderPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const isAdmin = Boolean(user?.is_admin || user?.is_supreme_admin);

  useEffect(() => setSearchDraft(search), [search]);

  useEffect(() => {
    if (authStatus === "checking") return;
    if (authStatus !== "authenticated" || !isAdmin || !accessToken) {
      setLoading(false);
      return;
    }

    const query: AdminOrderQuery = { limit: PAGE_SIZE, offset };
    if (search) query.search = search;
    if (orderStatus) query.status = orderStatus;
    if (paymentStatus) query.payment_status = paymentStatus;

    let active = true;
    setLoading(true);
    setError(null);
    api
      .listAdminOrders(accessToken, query)
      .then((value) => {
        if (active) setPage(value);
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof ApiError ? caught.message : "Could not load orders.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [accessToken, authStatus, isAdmin, offset, orderStatus, paymentStatus, search]);

  function updateQuery(updates: Record<string, string | undefined>, resetOffset = false) {
    const next = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(updates)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    if (resetOffset) next.delete("offset");
    const nextQuery = next.toString();
    router.replace(nextQuery ? `${pathname}?${nextQuery}` : pathname);
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateQuery({ search: searchDraft.trim() || undefined }, true);
  }

  const returnPath = useMemo(() => `${pathname}${queryString ? `?${queryString}` : ""}`, [pathname, queryString]);
  const pageNumber = Math.floor(offset / PAGE_SIZE) + 1;
  const pageCount = page ? Math.max(1, Math.ceil(page.total / PAGE_SIZE)) : 1;

  if (authStatus === "checking") return <LoadingState label="Checking admin access..." />;
  if (authStatus !== "authenticated") {
    return <ErrorState title="Login required" message="Sign in with an admin account to review orders." href="/login?next=/admin/orders" action="Login" />;
  }
  if (!isAdmin) {
    return <ErrorState title="Admin required" message="Order review is only available to store admins." href="/account" action="Return to account" />;
  }
  if (loading && !page) return <LoadingState label="Loading orders..." />;
  if (error && !page) {
    return <ErrorState title="Could not load orders" message={error} href="/admin/orders" action="Try again" />;
  }

  return (
    <section className="grid gap-5">
      <div className="surface p-5 sm:p-6">
        <p className="text-sm font-bold uppercase tracking-wide text-market-green">Admin Orders</p>
        <div className="mt-2 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-3xl font-black">Order review</h1>
            <p className="mt-2 text-sm text-ink-500">Read-only payment, customer, and order snapshots.</p>
          </div>
          <p className="text-sm font-bold text-ink-600">{formatCount(page?.total ?? 0)} orders</p>
        </div>

        <form onSubmit={submitSearch} className="mt-6 grid gap-3 lg:grid-cols-[minmax(14rem,1fr)_13rem_13rem_auto]" aria-label="Order filters">
          <label className="grid gap-1 text-sm font-bold text-ink-700">
            Search
            <input
              value={searchDraft}
              onChange={(event) => setSearchDraft(event.target.value)}
              placeholder="Order number or customer email"
              className="min-h-11 border border-ink-300 bg-white px-3 font-medium outline-none focus:border-market-green focus:ring-2 focus:ring-market-green/20"
            />
          </label>
          <label className="grid gap-1 text-sm font-bold text-ink-700">
            Order status
            <select
              value={orderStatus ?? ""}
              onChange={(event) => updateQuery({ status: event.target.value || undefined }, true)}
              className="min-h-11 border border-ink-300 bg-white px-3 font-medium outline-none focus:border-market-green"
            >
              <option value="">All order statuses</option>
              {ORDER_STATUSES.map((value) => <option key={value} value={value}>{titleCaseStatus(value)}</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-sm font-bold text-ink-700">
            Payment status
            <select
              value={paymentStatus ?? ""}
              onChange={(event) => updateQuery({ payment_status: event.target.value || undefined }, true)}
              className="min-h-11 border border-ink-300 bg-white px-3 font-medium outline-none focus:border-market-green"
            >
              <option value="">All payment statuses</option>
              {PAYMENT_STATUSES.map((value) => <option key={value} value={value}>{titleCaseStatus(value)}</option>)}
            </select>
          </label>
          <button type="submit" className="min-h-11 self-end bg-ink-900 px-5 text-sm font-bold text-white hover:bg-market-green">
            Search
          </button>
        </form>
      </div>

      {error ? <p role="alert" className="border border-market-red/30 bg-red-50 px-4 py-3 text-sm font-semibold text-market-red">{error}</p> : null}
      {loading ? <p role="status" className="text-sm font-semibold text-ink-500">Refreshing orders...</p> : null}

      {page && page.items.length === 0 ? (
        <EmptyState title="No orders found" message="No orders match the current search and status filters." href="/admin/orders" action="Clear filters" />
      ) : (
        <div className="grid gap-3">
          {page?.items.map((order) => {
            const presentation = getPaymentPresentation(order);
            const detailHref = `/admin/orders/${order.id}?return_to=${encodeURIComponent(returnPath)}`;
            return (
              <article key={order.id} className="surface p-4 sm:p-5">
                <div className="grid gap-4 lg:grid-cols-[1.15fr_1fr_auto] lg:items-center">
                  <div className="min-w-0">
                    <Link href={detailHref} className="text-lg font-black hover:text-market-green">{order.order_number}</Link>
                    <p className="mt-1 truncate text-sm font-semibold text-ink-700">{order.customer_name}</p>
                    <p className="truncate text-sm text-ink-500">{order.customer_email}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
                    <div><p className="text-xs font-bold uppercase text-ink-400">Total</p><p className="mt-1 font-black">{formatMoney(order.total_cents, order.currency)}</p></div>
                    <div><p className="text-xs font-bold uppercase text-ink-400">Items</p><p className="mt-1 font-bold">{order.item_quantity} in {order.item_line_count} lines</p></div>
                    <div className="col-span-2 sm:col-span-1"><p className="text-xs font-bold uppercase text-ink-400">Created</p><p className="mt-1 font-bold">{new Date(order.created_at).toLocaleString()}</p></div>
                  </div>
                  <div className="flex flex-wrap items-center gap-2 lg:flex-col lg:items-end">
                    <PaymentStatusPresentation presentation={presentation} compact />
                    <span className="border border-ink-200 bg-ink-50 px-2 py-1 text-xs font-bold uppercase text-ink-600">{titleCaseStatus(order.status)}</span>
                    <Link href={detailHref} className="text-sm font-black text-market-green hover:text-ink-900">Review order →</Link>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {page && page.total > 0 ? (
        <nav className="surface flex flex-wrap items-center justify-between gap-3 p-4" aria-label="Order pagination">
          <button
            type="button"
            disabled={offset === 0 || loading}
            onClick={() => updateQuery({ offset: String(Math.max(0, offset - PAGE_SIZE)) })}
            className="border border-ink-300 px-4 py-2 text-sm font-bold hover:border-market-green hover:text-market-green disabled:cursor-not-allowed disabled:opacity-40"
          >
            Previous
          </button>
          <p className="text-sm font-semibold text-ink-600">Page {pageNumber} of {pageCount}</p>
          <button
            type="button"
            disabled={offset + PAGE_SIZE >= page.total || loading}
            onClick={() => updateQuery({ offset: String(offset + PAGE_SIZE) })}
            className="border border-ink-300 px-4 py-2 text-sm font-bold hover:border-market-green hover:text-market-green disabled:cursor-not-allowed disabled:opacity-40"
          >
            Next
          </button>
        </nav>
      ) : null}
    </section>
  );
}
