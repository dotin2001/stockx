"use client";

import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import type { ListingRead, ProductSummary } from "@/lib/types";
import { formatMoney } from "@/lib/format";
import { ErrorState, LoadingState } from "@/components/ui/states";

export function SellForm({ requestedProduct }: { requestedProduct?: string }) {
  const { accessToken } = useAuth();
  const [products, setProducts] = useState<ProductSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<ListingRead | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .listProducts(100)
      .then((page) => {
        if (active) {
          setProducts(page.items);
        }
      })
      .catch((caught: unknown) => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "Could not load products.");
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken) {
      setError("Login required.");
      return;
    }
    const form = new FormData(event.currentTarget);
    setSubmitting(true);
    setError(null);
    setSuccess(null);
    try {
      const listing = await api.createListing(accessToken, {
        product_id: String(form.get("product_id") ?? ""),
        price_cents: Math.round(Number(form.get("price_dollars") ?? 0) * 100),
        currency: "USD"
      });
      setSuccess(listing);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not create listing.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <LoadingState label="Loading products for selling..." />;
  }

  if (products.length === 0) {
    return <ErrorState title="No sellable products" message="Seed catalog products before creating a listing." />;
  }

  const defaultProduct = products.find((product) => product.slug === requestedProduct) ?? products[0];

  return (
    <form onSubmit={submit} className="surface mx-auto grid max-w-2xl gap-5 p-6">
      <div>
        <p className="text-sm font-bold uppercase tracking-wide text-market-green">Sell</p>
        <h1 className="mt-2 text-3xl font-black">Create a listing</h1>
        <p className="mt-2 text-sm leading-6 text-ink-500">Choose an available seeded product and set your ask.</p>
      </div>
      <label className="grid gap-2 text-sm font-semibold">
        Product
        <select name="product_id" defaultValue={defaultProduct.id} className="border border-ink-200 px-3 py-3 font-normal">
          {products.map((product) => (
            <option key={product.id} value={product.id}>
              {product.name} ({formatMoney(product.lowest_ask_cents)})
            </option>
          ))}
        </select>
      </label>
      <label className="grid gap-2 text-sm font-semibold">
        Ask price in USD
        <input name="price_dollars" type="number" min="1" step="1" required className="border border-ink-200 px-3 py-3 font-normal" placeholder="250" />
      </label>
      {error ? <p className="border border-market-red/30 bg-red-50 px-3 py-2 text-sm font-semibold text-market-red">{error}</p> : null}
      {success ? <p className="border border-market-green/30 bg-market-mint px-3 py-2 text-sm font-semibold text-ink-800">Listing created with status {success.status}.</p> : null}
      <button type="submit" disabled={submitting} className="bg-ink-900 px-5 py-3 text-sm font-bold text-white hover:bg-market-green disabled:cursor-not-allowed disabled:opacity-60">
        {submitting ? "Creating..." : "Create Listing"}
      </button>
    </form>
  );
}
