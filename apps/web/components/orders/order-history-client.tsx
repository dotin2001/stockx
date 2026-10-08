"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { OrderPage } from "@/lib/types";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";

const PAGE_SIZE = 10;

export function OrderHistoryClient() {
  const { accessToken } = useAuth();
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<OrderPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    if (!accessToken) return;
    setLoading(true);
    try {
      setData(await api.listOrders(accessToken, PAGE_SIZE, offset));
      setError(null);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not load order history.");
    } finally {
      setLoading(false);
    }
  }, [accessToken, offset]);
  useEffect(() => { void load(); }, [load]);
  if (loading) return <LoadingState label="Loading orders..." />;
  if (error || !data) return <ErrorState title="Could not load orders" message={error ?? undefined} href="/orders" action="Try again" />;
  if (data.total === 0) return <EmptyState title="No orders yet" message="Confirmed development orders will appear here." href="/cart" action="View cart" />;
  return (
    <section className="mx-auto grid max-w-4xl gap-5">
      <div><p className="text-sm font-bold uppercase tracking-wide text-market-green">Account</p><h1 className="mt-2 text-3xl font-black">Order history</h1></div>
      {data.items.map((order) => <Link key={order.id} href={`/orders/${order.id}`} className="surface grid gap-3 p-5 hover:border-market-green sm:grid-cols-[1fr_auto]">
        <div><p className="font-black">{order.order_number}</p><p className="mt-1 text-sm text-ink-500">{new Date(order.created_at).toLocaleString()} · {order.items.length} line{order.items.length === 1 ? "" : "s"}</p><p className="mt-2 text-sm">{order.items[0]?.product_name}</p></div>
        <div className="sm:text-right"><p className="font-black">{formatMoney(order.total_cents, order.currency)}</p><p className="mt-1 text-xs font-bold uppercase text-market-green">{order.status} · {order.payment_status}</p></div>
      </Link>)}
      <div className="flex justify-between gap-4">
        <button type="button" onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))} disabled={offset === 0} className="border border-ink-900 px-4 py-2 text-sm font-bold disabled:opacity-40">Previous</button>
        <button type="button" onClick={() => setOffset(offset + PAGE_SIZE)} disabled={offset + data.items.length >= data.total} className="border border-ink-900 px-4 py-2 text-sm font-bold disabled:opacity-40">Next</button>
      </div>
    </section>
  );
}
