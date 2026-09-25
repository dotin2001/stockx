"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import { slugifyProductName } from "@/lib/slug";
import type { AdminProductRead, Category } from "@/lib/types";
import { ErrorState, LoadingState } from "@/components/ui/states";

type ProductFormState = {
  categoryId: string;
  name: string;
  priceDollars: string;
  size: string;
  imageUrl: string;
};

type FormResult =
  | {
      kind: "success";
      product: AdminProductRead;
    }
  | {
      kind: "partial";
      product: AdminProductRead;
      message: string;
    };

const initialFormState: ProductFormState = {
  categoryId: "",
  name: "",
  priceDollars: "",
  size: "",
  imageUrl: ""
};

function centsFromDollars(value: string): number {
  return Math.round(Number(value) * 100);
}

function isValidHttpUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

function validateForm(form: ProductFormState): string | null {
  if (!form.categoryId) {
    return "Choose a category.";
  }
  if (!form.name.trim()) {
    return "Enter a product name.";
  }
  if (!slugifyProductName(form.name)) {
    return "Enter a product name with letters or numbers.";
  }
  if (centsFromDollars(form.priceDollars) <= 0) {
    return "Enter a price greater than zero.";
  }
  if (!form.size.trim()) {
    return "Enter an initial size.";
  }
  if (!form.imageUrl.trim() || !isValidHttpUrl(form.imageUrl)) {
    return "Enter a valid http or https image URL.";
  }
  return null;
}

export function AdminProductForm() {
  const { accessToken, status, user } = useAuth();
  const [categories, setCategories] = useState<Category[]>([]);
  const [loadingCategories, setLoadingCategories] = useState(false);
  const [categoryError, setCategoryError] = useState<string | null>(null);
  const [form, setForm] = useState<ProductFormState>(initialFormState);
  const [formError, setFormError] = useState<string | null>(null);
  const [result, setResult] = useState<FormResult | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const generatedSlug = useMemo(() => slugifyProductName(form.name), [form.name]);

  useEffect(() => {
    if (status !== "authenticated" || !user?.is_admin) {
      return;
    }

    let active = true;
    setLoadingCategories(true);
    setCategoryError(null);
    api
      .listCategories()
      .then((items) => {
        if (active) {
          setCategories(items);
          setForm((current) => ({
            ...current,
            categoryId: current.categoryId || items[0]?.id || ""
          }));
        }
      })
      .catch((caught: unknown) => {
        if (active) {
          setCategoryError(caught instanceof Error ? caught.message : "Could not load categories.");
        }
      })
      .finally(() => {
        if (active) {
          setLoadingCategories(false);
        }
      });

    return () => {
      active = false;
    };
  }, [status, user?.is_admin]);

  function updateField(field: keyof ProductFormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
    setFormError(null);
    setResult(null);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken) {
      setFormError("Login required.");
      return;
    }

    const validationError = validateForm(form);
    if (validationError) {
      setFormError(validationError);
      return;
    }

    setSubmitting(true);
    setFormError(null);
    setResult(null);

    try {
      const product = await api.createAdminProduct(accessToken, {
        category_id: form.categoryId,
        name: form.name.trim(),
        slug: generatedSlug,
        brand: null,
        description: null,
        image_url: form.imageUrl.trim(),
        lowest_ask_cents: centsFromDollars(form.priceDollars),
        total_sold: 0
      });

      try {
        await api.createAdminProductVariant(accessToken, product.id, {
          size: form.size.trim(),
          color: null,
          sku: null
        });
        setResult({ kind: "success", product });
        setForm({ ...initialFormState, categoryId: categories[0]?.id || "" });
      } catch (caught) {
        const message = caught instanceof ApiError ? caught.message : "The initial size could not be created.";
        setResult({
          kind: "partial",
          product,
          message: `Product was created, but the initial size was not saved. ${message}`
        });
      }
    } catch (caught) {
      if (caught instanceof ApiError && caught.code === "product_slug_exists") {
        setFormError("A product already exists with this generated slug. Change the product name and try again.");
      } else {
        setFormError(caught instanceof ApiError ? caught.message : "Could not create product.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (status === "checking") {
    return <LoadingState label="Checking admin access..." />;
  }

  if (status !== "authenticated") {
    return (
      <div className="surface mx-auto max-w-xl px-6 py-10 text-center">
        <h1 className="text-3xl font-black">Login required</h1>
        <p className="mt-3 text-sm leading-6 text-ink-500">Sign in with an admin account before creating catalog products.</p>
        <Link href="/login" className="mt-6 inline-flex bg-market-green px-5 py-3 text-sm font-bold text-white hover:bg-ink-900">
          Log in
        </Link>
      </div>
    );
  }

  if (!user?.is_admin) {
    return (
      <div className="surface mx-auto max-w-xl px-6 py-10 text-center">
        <p className="text-sm font-bold uppercase tracking-wide text-market-red">Admin required</p>
        <h1 className="mt-2 text-3xl font-black">Product creation is admin-only</h1>
        <p className="mt-3 text-sm leading-6 text-ink-500">Store catalog products are managed by admins. Customer accounts can browse, cart, watch, checkout, and message the store.</p>
        <Link href="/account" className="mt-6 inline-flex border border-ink-900 px-5 py-3 text-sm font-bold text-ink-900 hover:bg-ink-900 hover:text-white">
          Return to Account
        </Link>
      </div>
    );
  }

  if (loadingCategories) {
    return <LoadingState label="Loading categories..." />;
  }

  if (categoryError) {
    return <ErrorState title="Could not load categories" message={categoryError} href="/admin/products/new" action="Try again" />;
  }

  return (
    <form onSubmit={submit} className="surface mx-auto grid w-full max-w-3xl gap-5 p-6">
      <div>
        <p className="text-sm font-bold uppercase tracking-wide text-market-green">Admin catalog</p>
        <h1 className="mt-2 text-3xl font-black">Add product</h1>
        <p className="mt-2 text-sm leading-6 text-ink-500">Create a public catalog product and its first size variant.</p>
      </div>
      <label className="grid gap-2 text-sm font-semibold">
        Category
        <select
          name="category_id"
          required
          value={form.categoryId}
          onChange={(event) => updateField("categoryId", event.target.value)}
          className="border border-ink-200 px-3 py-3 font-normal"
          disabled={submitting || categories.length === 0}
        >
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </select>
      </label>
      <label className="grid gap-2 text-sm font-semibold">
        Product name
        <input
          name="name"
          required
          value={form.name}
          onChange={(event) => updateField("name", event.target.value)}
          className="border border-ink-200 px-3 py-3 font-normal"
          placeholder="Nike Dunk Low Custom"
          disabled={submitting}
        />
      </label>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="grid gap-2 text-sm font-semibold">
          Price in USD
          <input
            name="price_dollars"
            required
            type="number"
            min="0.01"
            step="0.01"
            value={form.priceDollars}
            onChange={(event) => updateField("priceDollars", event.target.value)}
            className="border border-ink-200 px-3 py-3 font-normal"
            placeholder="250"
            disabled={submitting}
          />
        </label>
        <label className="grid gap-2 text-sm font-semibold">
          Initial size
          <input
            name="size"
            required
            value={form.size}
            onChange={(event) => updateField("size", event.target.value)}
            className="border border-ink-200 px-3 py-3 font-normal"
            placeholder="10"
            disabled={submitting}
          />
        </label>
      </div>
      <label className="grid gap-2 text-sm font-semibold">
        Image URL
        <input
          name="image_url"
          required
          type="url"
          value={form.imageUrl}
          onChange={(event) => updateField("imageUrl", event.target.value)}
          className="border border-ink-200 px-3 py-3 font-normal"
          placeholder="https://example.com/product.jpg"
          disabled={submitting}
        />
      </label>
      <div className="border border-ink-200 bg-ink-50 px-3 py-2 text-xs font-semibold text-ink-600">
        Generated slug: <span className="text-ink-900">{generatedSlug || "product-name"}</span>
      </div>
      {formError ? <p className="border border-market-red/30 bg-red-50 px-3 py-2 text-sm font-semibold text-market-red">{formError}</p> : null}
      {result ? (
        <div className={`border px-3 py-2 text-sm font-semibold ${result.kind === "partial" ? "border-market-red/30 bg-red-50 text-market-red" : "border-market-green/30 bg-market-mint text-ink-800"}`}>
          <p>{result.kind === "partial" ? result.message : "Product created with initial size."}</p>
          <Link href={`/product/${result.product.slug}`} className="mt-2 inline-flex text-ink-900 underline decoration-market-green underline-offset-4 hover:text-market-green">
            View product
          </Link>
        </div>
      ) : null}
      <button
        type="submit"
        disabled={submitting || categories.length === 0}
        className="bg-ink-900 px-5 py-3 text-sm font-bold text-white hover:bg-market-green disabled:cursor-not-allowed disabled:opacity-60"
      >
        {submitting ? "Creating..." : "Create Product"}
      </button>
    </form>
  );
}
