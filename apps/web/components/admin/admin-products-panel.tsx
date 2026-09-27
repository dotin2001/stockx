"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import { formatCount, formatMoney } from "@/lib/format";
import type { AdminProductInventoryItem, AdminProductRead, Category, ListingStatus, ProductVariant, UUID } from "@/lib/types";
import { ErrorState, LoadingState } from "@/components/ui/states";

type CatalogFilter = "active" | "archived" | "all";
type InventoryFilter = "all" | "in-stock" | "out-of-stock" | "unavailable";

type ProductEditState = {
  categoryId: string;
  name: string;
  slug: string;
  brand: string;
  description: string;
  imageUrl: string;
  priceDollars: string;
  totalSold: string;
};

type VariantDraft = {
  size: string;
  color: string;
  sku: string;
};

type ListingCreateDraft = {
  variantId: string;
  priceDollars: string;
  currency: string;
  availableQuantity: string;
  status: ListingStatus;
};

const emptyVariantDraft: VariantDraft = {
  size: "",
  color: "",
  sku: ""
};

const emptyListingCreateDraft: ListingCreateDraft = {
  variantId: "",
  priceDollars: "",
  currency: "USD",
  availableQuantity: "1",
  status: "active"
};

function centsToDollars(value: number | null): string {
  return value === null ? "" : String(value / 100);
}

function centsFromDollars(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  return Math.round(Number(trimmed) * 100);
}

function nullableText(value: string): string | null {
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function editStateFromProduct(product: AdminProductRead): ProductEditState {
  return {
    categoryId: product.category.id,
    name: product.name,
    slug: product.slug,
    brand: product.brand ?? "",
    description: product.description ?? "",
    imageUrl: product.image_url ?? "",
    priceDollars: centsToDollars(product.lowest_ask_cents),
    totalSold: String(product.total_sold)
  };
}

function variantDraftFromVariant(variant: ProductVariant): VariantDraft {
  return {
    size: variant.size ?? "",
    color: variant.color ?? "",
    sku: variant.sku ?? ""
  };
}

function variantLabel(item: AdminProductInventoryItem): string {
  if (!item.variant) {
    return "Base";
  }
  return [item.variant.size, item.variant.color, item.variant.sku].filter(Boolean).join(" / ") || "Variant";
}

function productMatchesInventory(product: AdminProductRead, filter: InventoryFilter): boolean {
  if (filter === "all") {
    return true;
  }
  if (filter === "in-stock") {
    return product.inventory_summary.total_available_quantity > 0;
  }
  if (filter === "out-of-stock") {
    return product.inventory_summary.total_listings > 0 && product.inventory_summary.total_available_quantity === 0;
  }
  return product.inventory_summary.total_listings === 0 || product.inventory_summary.active_listings === 0;
}

function statusTone(status: string): string {
  if (status === "active") {
    return "border-market-green/30 bg-market-mint text-ink-800";
  }
  if (status === "sold") {
    return "border-market-red/30 bg-red-50 text-market-red";
  }
  return "border-ink-200 bg-ink-50 text-ink-600";
}

function listingCreatePayloadFromDraft(draft: ListingCreateDraft):
  | {
      payload: {
        product_variant_id: UUID | null;
        price_cents: number;
        currency: string;
        available_quantity: number;
        status: ListingStatus;
      };
    }
  | { error: string } {
  const priceCents = centsFromDollars(draft.priceDollars);
  if (priceCents === null || !Number.isFinite(priceCents) || priceCents <= 0) {
    return { error: "Listing price must be greater than zero." };
  }

  const quantityText = draft.availableQuantity.trim();
  const availableQuantity = Number(quantityText);
  if (!quantityText || !Number.isInteger(availableQuantity) || availableQuantity < 0) {
    return { error: "Initial quantity must be a whole number of zero or greater." };
  }

  const currency = draft.currency.trim().toUpperCase();
  if (!/^[A-Z]{3}$/.test(currency)) {
    return { error: "Currency must be a three-letter code." };
  }

  return {
    payload: {
      product_variant_id: draft.variantId ? draft.variantId : null,
      price_cents: priceCents,
      currency,
      available_quantity: availableQuantity,
      status: draft.status
    }
  };
}

export function AdminProductsPanel() {
  const { status, user, accessToken } = useAuth();
  const [products, setProducts] = useState<AdminProductRead[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [catalogFilter, setCatalogFilter] = useState<CatalogFilter>("active");
  const [inventoryFilter, setInventoryFilter] = useState<InventoryFilter>("all");
  const [scan, setScan] = useState("");
  const [selectedId, setSelectedId] = useState<UUID | null>(null);
  const [editState, setEditState] = useState<ProductEditState | null>(null);
  const [variantDraft, setVariantDraft] = useState<VariantDraft>(emptyVariantDraft);
  const [listingDraft, setListingDraft] = useState<ListingCreateDraft>(emptyListingCreateDraft);
  const [variantEdits, setVariantEdits] = useState<Record<UUID, VariantDraft>>({});
  const [quantityDrafts, setQuantityDrafts] = useState<Record<UUID, string>>({});
  const [statusDrafts, setStatusDrafts] = useState<Record<UUID, ListingStatus>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [mutating, setMutating] = useState<string | null>(null);

  const selectedProduct = useMemo(
    () => products.find((product) => product.id === selectedId) ?? null,
    [products, selectedId]
  );

  const filteredProducts = useMemo(() => {
    const query = scan.trim().toLowerCase();
    return products.filter((product) => {
      const matchesScan =
        !query ||
        [product.name, product.slug, product.brand ?? "", product.category.name].some((value) =>
          value.toLowerCase().includes(query)
        );
      return matchesScan && productMatchesInventory(product, inventoryFilter);
    });
  }, [inventoryFilter, products, scan]);

  const loadProducts = useCallback(
    async (nextFilter: CatalogFilter, nextSelectedId: UUID | null) => {
      if (!accessToken || !user?.is_admin) {
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const archived = nextFilter === "all" ? undefined : nextFilter === "archived";
        const [productPage, categoryItems] = await Promise.all([
          api.listAdminProducts(accessToken, archived, 100, 0),
          api.listCategories()
        ]);
        setProducts(productPage.items);
        setCategories(categoryItems);
        const selected = productPage.items.find((product) => product.id === nextSelectedId) ?? productPage.items[0] ?? null;
        setSelectedId(selected?.id ?? null);
        setEditState(selected ? editStateFromProduct(selected) : null);
      } catch (caught) {
        setError(caught instanceof ApiError ? caught.message : "Could not load managed products.");
      } finally {
        setLoading(false);
      }
    },
    [accessToken, user?.is_admin]
  );

  useEffect(() => {
    if (status === "checking") {
      return;
    }
    void loadProducts(catalogFilter, null);
  }, [catalogFilter, loadProducts, status]);

  useEffect(() => {
    if (!selectedProduct) {
      setEditState(null);
      setVariantEdits({});
      setListingDraft(emptyListingCreateDraft);
      setQuantityDrafts({});
      setStatusDrafts({});
      return;
    }
    setEditState(editStateFromProduct(selectedProduct));
    setVariantEdits(
      Object.fromEntries(selectedProduct.variants.map((variant) => [variant.id, variantDraftFromVariant(variant)]))
    );
    setListingDraft(emptyListingCreateDraft);
    setQuantityDrafts(Object.fromEntries(selectedProduct.inventory_items.map((item) => [item.id, "1"])));
    setStatusDrafts(Object.fromEntries(selectedProduct.inventory_items.map((item) => [item.id, item.status])));
  }, [selectedProduct]);

  async function reloadAfterMutation(message: string) {
    setNotice(message);
    setMutationError(null);
    await loadProducts(catalogFilter, selectedId);
  }

  async function submitProductUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken || !selectedProduct || !editState) {
      return;
    }
    const priceCents = centsFromDollars(editState.priceDollars);
    if (priceCents !== null && priceCents < 0) {
      setMutationError("Price cannot be negative.");
      return;
    }
    const totalSold = Number(editState.totalSold);
    if (!Number.isInteger(totalSold) || totalSold < 0) {
      setMutationError("Total sold must be zero or greater.");
      return;
    }

    setMutating("product");
    setMutationError(null);
    setNotice(null);
    try {
      const updated = await api.updateAdminProduct(accessToken, selectedProduct.id, {
        category_id: editState.categoryId,
        name: editState.name.trim(),
        slug: editState.slug.trim(),
        brand: nullableText(editState.brand),
        description: nullableText(editState.description),
        image_url: nullableText(editState.imageUrl),
        lowest_ask_cents: priceCents,
        total_sold: totalSold
      });
      setProducts((current) => current.map((product) => (product.id === updated.id ? updated : product)));
      setNotice("Product updated.");
    } catch (caught) {
      setMutationError(caught instanceof ApiError ? caught.message : "Could not update product.");
    } finally {
      setMutating(null);
    }
  }

  async function toggleArchive(product: AdminProductRead) {
    if (!accessToken) {
      return;
    }
    setMutating(`archive-${product.id}`);
    setMutationError(null);
    setNotice(null);
    try {
      const updated = product.archived_at
        ? await api.restoreAdminProduct(accessToken, product.id)
        : await api.archiveAdminProduct(accessToken, product.id);
      setProducts((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setNotice(updated.archived_at ? "Product archived." : "Product restored.");
    } catch (caught) {
      setMutationError(caught instanceof ApiError ? caught.message : "Could not update catalog state.");
    } finally {
      setMutating(null);
    }
  }

  async function createVariant(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken || !selectedProduct) {
      return;
    }
    setMutating("variant-create");
    setMutationError(null);
    setNotice(null);
    try {
      await api.createAdminProductVariant(accessToken, selectedProduct.id, {
        size: nullableText(variantDraft.size),
        color: nullableText(variantDraft.color),
        sku: nullableText(variantDraft.sku)
      });
      setVariantDraft(emptyVariantDraft);
      await reloadAfterMutation("Variant created.");
    } catch (caught) {
      setMutationError(caught instanceof ApiError ? caught.message : "Could not create variant.");
    } finally {
      setMutating(null);
    }
  }

  async function updateVariant(variant: ProductVariant) {
    if (!accessToken || !selectedProduct) {
      return;
    }
    const draft = variantEdits[variant.id] ?? variantDraftFromVariant(variant);
    setMutating(`variant-${variant.id}`);
    setMutationError(null);
    setNotice(null);
    try {
      await api.updateAdminProductVariant(accessToken, variant.id, {
        size: nullableText(draft.size),
        color: nullableText(draft.color),
        sku: nullableText(draft.sku)
      });
      await reloadAfterMutation("Variant updated.");
    } catch (caught) {
      setMutationError(caught instanceof ApiError ? caught.message : "Could not update variant.");
    } finally {
      setMutating(null);
    }
  }

  async function deleteVariant(variant: ProductVariant) {
    if (!accessToken) {
      return;
    }
    setMutating(`variant-delete-${variant.id}`);
    setMutationError(null);
    setNotice(null);
    try {
      await api.deleteAdminProductVariant(accessToken, variant.id);
      await reloadAfterMutation("Variant removed.");
    } catch (caught) {
      setMutationError(caught instanceof ApiError ? caught.message : "Could not remove variant.");
    } finally {
      setMutating(null);
    }
  }

  async function createListing(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!accessToken || !selectedProduct) {
      return;
    }
    const result = listingCreatePayloadFromDraft(listingDraft);
    if ("error" in result) {
      setMutationError(result.error);
      return;
    }

    setMutating("listing-create");
    setMutationError(null);
    setNotice(null);
    try {
      await api.createAdminProductListing(accessToken, selectedProduct.id, result.payload);
      setListingDraft(emptyListingCreateDraft);
      await reloadAfterMutation("Listing created.");
    } catch (caught) {
      setMutationError(caught instanceof ApiError ? caught.message : "Could not create listing.");
    } finally {
      setMutating(null);
    }
  }

  async function adjustQuantity(item: AdminProductInventoryItem, direction: 1 | -1) {
    if (!accessToken) {
      return;
    }
    const amount = Number(quantityDrafts[item.id] ?? "1");
    if (!Number.isInteger(amount) || amount <= 0) {
      setMutationError("Quantity adjustment must be a positive whole number.");
      return;
    }
    setMutating(`quantity-${item.id}`);
    setMutationError(null);
    setNotice(null);
    try {
      await api.adjustAdminListingQuantity(accessToken, item.id, { adjustment: amount * direction });
      await reloadAfterMutation("Inventory quantity updated.");
    } catch (caught) {
      setMutationError(caught instanceof ApiError ? caught.message : "Could not update quantity.");
    } finally {
      setMutating(null);
    }
  }

  async function updateInventoryStatus(item: AdminProductInventoryItem) {
    if (!accessToken) {
      return;
    }
    setMutating(`status-${item.id}`);
    setMutationError(null);
    setNotice(null);
    try {
      await api.updateAdminListingStatus(accessToken, item.id, { status: statusDrafts[item.id] ?? item.status });
      await reloadAfterMutation("Inventory status updated.");
    } catch (caught) {
      setMutationError(caught instanceof ApiError ? caught.message : "Could not update status.");
    } finally {
      setMutating(null);
    }
  }

  if (status === "checking" || loading) {
    return <LoadingState label="Loading admin products..." />;
  }

  if (status !== "authenticated") {
    return (
      <section className="surface mx-auto max-w-2xl p-6">
        <p className="text-sm font-bold uppercase tracking-wide text-market-green">Login required</p>
        <h1 className="mt-2 text-3xl font-black">Admin products require login</h1>
        <Link href="/login" className="mt-6 inline-flex bg-market-green px-5 py-3 text-sm font-bold text-white hover:bg-ink-900">
          Login
        </Link>
      </section>
    );
  }

  if (!user?.is_admin) {
    return <ErrorState title="Admin required" message="Product management is only available to store admins." href="/account" action="Return to account" />;
  }

  if (error) {
    return <ErrorState title="Could not load products" message={error} href="/admin/products" action="Try again" />;
  }

  return (
    <section className="grid gap-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-sm font-bold uppercase tracking-wide text-market-green">Admin Products</p>
          <h1 className="mt-2 text-3xl font-black">Product management</h1>
        </div>
        <Link href="/admin/products/new" className="bg-ink-900 px-5 py-3 text-sm font-bold text-white hover:bg-market-green">
          New Product
        </Link>
      </div>

      <div className="surface grid gap-4 p-4">
        <div className="grid gap-3 lg:grid-cols-[1fr_auto_auto]">
          <label className="grid gap-2 text-sm font-semibold">
            Scan products
            <input
              value={scan}
              onChange={(event) => setScan(event.target.value)}
              className="border border-ink-200 px-3 py-3 font-normal"
              placeholder="Name, slug, brand, category"
            />
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Catalog
            <select
              value={catalogFilter}
              onChange={(event) => {
                setSelectedId(null);
                setCatalogFilter(event.target.value as CatalogFilter);
              }}
              className="border border-ink-200 px-3 py-3 font-normal"
            >
              <option value="active">Active</option>
              <option value="archived">Archived</option>
              <option value="all">All</option>
            </select>
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Inventory
            <select
              value={inventoryFilter}
              onChange={(event) => setInventoryFilter(event.target.value as InventoryFilter)}
              className="border border-ink-200 px-3 py-3 font-normal"
            >
              <option value="all">All</option>
              <option value="in-stock">In stock</option>
              <option value="out-of-stock">Out of stock</option>
              <option value="unavailable">Unavailable</option>
            </select>
          </label>
        </div>
        <p className="text-sm font-semibold text-ink-500">
          {formatCount(filteredProducts.length)} of {formatCount(products.length)} products
        </p>
      </div>

      {mutationError ? <p className="border border-market-red/30 bg-red-50 px-3 py-2 text-sm font-semibold text-market-red">{mutationError}</p> : null}
      {notice ? <p className="border border-market-green/30 bg-market-mint px-3 py-2 text-sm font-semibold text-ink-800">{notice}</p> : null}

      {products.length === 0 ? (
        <div className="surface p-6 text-sm font-semibold text-ink-600">No managed products found.</div>
      ) : (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(360px,440px)]">
          <div className="surface overflow-hidden">
            <div className="grid grid-cols-[1.5fr_0.9fr_0.9fr_auto] gap-3 border-b border-ink-200 bg-ink-50 px-4 py-3 text-xs font-bold uppercase text-ink-500">
              <span>Product</span>
              <span>Catalog</span>
              <span>Inventory</span>
              <span>Action</span>
            </div>
            <div className="divide-y divide-ink-200">
              {filteredProducts.length === 0 ? (
                <p className="px-4 py-6 text-sm font-semibold text-ink-600">No products match the current filters.</p>
              ) : (
                filteredProducts.map((product) => (
                  <article
                    key={product.id}
                    className={`grid gap-3 px-4 py-4 text-sm md:grid-cols-[1.5fr_0.9fr_0.9fr_auto] md:items-center ${selectedId === product.id ? "bg-market-mint/60" : "bg-white"}`}
                  >
                    <div className="min-w-0">
                      <h2 className="truncate text-base font-black">{product.name}</h2>
                      <p className="mt-1 truncate text-ink-500">{product.brand ?? product.category.name}</p>
                      <p className="mt-1 truncate text-xs font-semibold text-ink-500">{product.slug}</p>
                    </div>
                    <div>
                      <span className={`inline-flex border px-2 py-1 text-xs font-bold uppercase ${product.archived_at ? "border-ink-200 bg-ink-50 text-ink-600" : "border-market-green/30 bg-market-mint text-ink-800"}`}>
                        {product.archived_at ? "Archived" : "Active"}
                      </span>
                      <p className="mt-2 text-xs font-semibold text-ink-500">{product.category.name}</p>
                    </div>
                    <div>
                      <p className="font-bold">{formatCount(product.inventory_summary.total_available_quantity)} available</p>
                      <p className="mt-1 text-xs text-ink-500">
                        {formatCount(product.inventory_summary.active_listings)} active / {formatCount(product.inventory_summary.total_listings)} listings
                      </p>
                      <p className="mt-1 text-xs text-ink-500">
                        {formatMoney(product.inventory_summary.lowest_active_price_cents)}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setSelectedId(product.id)}
                      className="border border-ink-900 px-4 py-2 text-xs font-bold text-ink-900 hover:bg-ink-900 hover:text-white"
                    >
                      Edit
                    </button>
                  </article>
                ))
              )}
            </div>
          </div>

          <aside className="surface p-5">
            {!selectedProduct || !editState ? (
              <p className="text-sm font-semibold text-ink-600">Select a product to edit.</p>
            ) : (
              <div className="grid gap-6">
                <form onSubmit={submitProductUpdate} className="grid gap-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-bold uppercase text-market-green">Catalog</p>
                      <h2 className="mt-1 text-xl font-black">{selectedProduct.name}</h2>
                    </div>
                    <button
                      type="button"
                      onClick={() => void toggleArchive(selectedProduct)}
                      disabled={mutating === `archive-${selectedProduct.id}`}
                      className="border border-ink-300 px-3 py-2 text-xs font-bold text-ink-900 hover:border-market-green hover:text-market-green disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {selectedProduct.archived_at ? "Restore" : "Archive"}
                    </button>
                  </div>
                  <label className="grid gap-2 text-sm font-semibold">
                    Category
                    <select
                      value={editState.categoryId}
                      onChange={(event) => setEditState({ ...editState, categoryId: event.target.value })}
                      className="border border-ink-200 px-3 py-3 font-normal"
                    >
                      {categories.map((category) => (
                        <option key={category.id} value={category.id}>
                          {category.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="grid gap-2 text-sm font-semibold">
                    Name
                    <input value={editState.name} onChange={(event) => setEditState({ ...editState, name: event.target.value })} className="border border-ink-200 px-3 py-3 font-normal" />
                  </label>
                  <label className="grid gap-2 text-sm font-semibold">
                    Slug
                    <input value={editState.slug} onChange={(event) => setEditState({ ...editState, slug: event.target.value })} className="border border-ink-200 px-3 py-3 font-normal" />
                  </label>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <label className="grid gap-2 text-sm font-semibold">
                      Brand
                      <input value={editState.brand} onChange={(event) => setEditState({ ...editState, brand: event.target.value })} className="border border-ink-200 px-3 py-3 font-normal" />
                    </label>
                    <label className="grid gap-2 text-sm font-semibold">
                      Price USD
                      <input type="number" min="0" step="0.01" value={editState.priceDollars} onChange={(event) => setEditState({ ...editState, priceDollars: event.target.value })} className="border border-ink-200 px-3 py-3 font-normal" />
                    </label>
                  </div>
                  <label className="grid gap-2 text-sm font-semibold">
                    Image URL
                    <input value={editState.imageUrl} onChange={(event) => setEditState({ ...editState, imageUrl: event.target.value })} className="border border-ink-200 px-3 py-3 font-normal" />
                  </label>
                  <label className="grid gap-2 text-sm font-semibold">
                    Description
                    <textarea value={editState.description} onChange={(event) => setEditState({ ...editState, description: event.target.value })} className="min-h-24 border border-ink-200 px-3 py-3 font-normal" />
                  </label>
                  <label className="grid gap-2 text-sm font-semibold">
                    Total sold
                    <input type="number" min="0" step="1" value={editState.totalSold} onChange={(event) => setEditState({ ...editState, totalSold: event.target.value })} className="border border-ink-200 px-3 py-3 font-normal" />
                  </label>
                  <button type="submit" disabled={mutating === "product"} className="bg-ink-900 px-5 py-3 text-sm font-bold text-white hover:bg-market-green disabled:cursor-not-allowed disabled:opacity-60">
                    {mutating === "product" ? "Saving..." : "Save Product"}
                  </button>
                </form>

                <div className="grid gap-3 border-t border-ink-200 pt-5">
                  <div>
                    <p className="text-xs font-bold uppercase text-market-green">Variants</p>
                    <h3 className="mt-1 text-lg font-black">Variant management</h3>
                  </div>
                  {selectedProduct.variants.length === 0 ? (
                    <p className="border border-ink-200 bg-ink-50 px-3 py-2 text-sm font-semibold text-ink-600">No variants yet.</p>
                  ) : (
                    selectedProduct.variants.map((variant) => {
                      const draft = variantEdits[variant.id] ?? variantDraftFromVariant(variant);
                      return (
                        <div key={variant.id} className="grid gap-2 border border-ink-200 p-3">
                          <div className="grid gap-2 sm:grid-cols-3">
                            <input value={draft.size} onChange={(event) => setVariantEdits((current) => ({ ...current, [variant.id]: { ...draft, size: event.target.value } }))} className="border border-ink-200 px-3 py-2 text-sm" placeholder="Size" />
                            <input value={draft.color} onChange={(event) => setVariantEdits((current) => ({ ...current, [variant.id]: { ...draft, color: event.target.value } }))} className="border border-ink-200 px-3 py-2 text-sm" placeholder="Color" />
                            <input value={draft.sku} onChange={(event) => setVariantEdits((current) => ({ ...current, [variant.id]: { ...draft, sku: event.target.value } }))} className="border border-ink-200 px-3 py-2 text-sm" placeholder="SKU" />
                          </div>
                          <div className="flex flex-wrap gap-2">
                            <button type="button" onClick={() => void updateVariant(variant)} disabled={mutating === `variant-${variant.id}`} className="border border-ink-900 px-3 py-2 text-xs font-bold hover:bg-ink-900 hover:text-white disabled:cursor-not-allowed disabled:opacity-60">
                              Update
                            </button>
                            <button type="button" onClick={() => void deleteVariant(variant)} disabled={mutating === `variant-delete-${variant.id}`} className="border border-market-red/40 px-3 py-2 text-xs font-bold text-market-red hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60">
                              Remove
                            </button>
                          </div>
                        </div>
                      );
                    })
                  )}
                  <form onSubmit={createVariant} className="grid gap-2 border border-ink-200 bg-ink-50 p-3">
                    <div className="grid gap-2 sm:grid-cols-3">
                      <input value={variantDraft.size} onChange={(event) => setVariantDraft({ ...variantDraft, size: event.target.value })} className="border border-ink-200 bg-white px-3 py-2 text-sm" placeholder="Size" />
                      <input value={variantDraft.color} onChange={(event) => setVariantDraft({ ...variantDraft, color: event.target.value })} className="border border-ink-200 bg-white px-3 py-2 text-sm" placeholder="Color" />
                      <input value={variantDraft.sku} onChange={(event) => setVariantDraft({ ...variantDraft, sku: event.target.value })} className="border border-ink-200 bg-white px-3 py-2 text-sm" placeholder="SKU" />
                    </div>
                    <button type="submit" disabled={mutating === "variant-create"} className="bg-ink-900 px-4 py-2 text-xs font-bold text-white hover:bg-market-green disabled:cursor-not-allowed disabled:opacity-60">
                      {mutating === "variant-create" ? "Creating..." : "Create Variant"}
                    </button>
                  </form>
                </div>

                <div className="grid gap-3 border-t border-ink-200 pt-5">
                  <div>
                    <p className="text-xs font-bold uppercase text-market-green">Inventory</p>
                    <h3 className="mt-1 text-lg font-black">Listing inventory</h3>
                  </div>
                  {user.is_supreme_admin ? (
                    <>
                      <form onSubmit={createListing} className="grid gap-3 border border-ink-200 bg-ink-50 p-3">
                        <div className="grid gap-2 sm:grid-cols-2">
                          <label className="grid gap-1 text-xs font-bold uppercase text-ink-500">
                            Variant
                            <select value={listingDraft.variantId} onChange={(event) => setListingDraft((current) => ({ ...current, variantId: event.target.value }))} className="border border-ink-200 bg-white px-3 py-2 text-sm font-normal text-ink-900">
                              <option value="">Base product</option>
                              {selectedProduct.variants.map((variant) => (
                                <option key={variant.id} value={variant.id}>
                                  {[variant.size, variant.color, variant.sku].filter(Boolean).join(" / ") || "Variant"}
                                </option>
                              ))}
                            </select>
                          </label>
                          <label className="grid gap-1 text-xs font-bold uppercase text-ink-500">
                            Price USD
                            <input type="number" min="0.01" step="0.01" value={listingDraft.priceDollars} onChange={(event) => setListingDraft((current) => ({ ...current, priceDollars: event.target.value }))} className="border border-ink-200 bg-white px-3 py-2 text-sm font-normal text-ink-900" />
                          </label>
                        </div>
                        <div className="grid gap-2 sm:grid-cols-3">
                          <label className="grid gap-1 text-xs font-bold uppercase text-ink-500">
                            Currency
                            <input value={listingDraft.currency} onChange={(event) => setListingDraft((current) => ({ ...current, currency: event.target.value.toUpperCase() }))} className="border border-ink-200 bg-white px-3 py-2 text-sm font-normal text-ink-900" maxLength={3} />
                          </label>
                          <label className="grid gap-1 text-xs font-bold uppercase text-ink-500">
                            Initial quantity
                            <input type="number" min="0" step="1" value={listingDraft.availableQuantity} onChange={(event) => setListingDraft((current) => ({ ...current, availableQuantity: event.target.value }))} className="border border-ink-200 bg-white px-3 py-2 text-sm font-normal text-ink-900" />
                          </label>
                          <label className="grid gap-1 text-xs font-bold uppercase text-ink-500">
                            Status
                            <select value={listingDraft.status} onChange={(event) => setListingDraft((current) => ({ ...current, status: event.target.value as ListingStatus }))} className="border border-ink-200 bg-white px-3 py-2 text-sm font-normal text-ink-900">
                              <option value="active">Active</option>
                              <option value="sold">Sold</option>
                              <option value="cancelled">Cancelled</option>
                            </select>
                          </label>
                        </div>
                        <button type="submit" disabled={mutating === "listing-create"} className="bg-ink-900 px-4 py-2 text-xs font-bold text-white hover:bg-market-green disabled:cursor-not-allowed disabled:opacity-60">
                          {mutating === "listing-create" ? "Creating..." : "Create Listing"}
                        </button>
                      </form>
                      {selectedProduct.inventory_items.length === 0 ? (
                        <p className="border border-ink-200 bg-white px-3 py-2 text-sm font-semibold text-ink-600">No sellable listings yet.</p>
                      ) : (
                        selectedProduct.inventory_items.map((item) => (
                          <div key={item.id} className="grid gap-3 border border-ink-200 p-3">
                            <div className="flex flex-wrap items-start justify-between gap-2">
                              <div>
                                <p className="font-bold">{variantLabel(item)}</p>
                                <p className="mt-1 text-xs font-semibold text-ink-500">{formatMoney(item.price_cents, item.currency)}</p>
                              </div>
                              <span className={`border px-2 py-1 text-xs font-bold uppercase ${statusTone(item.status)}`}>{item.status}</span>
                            </div>
                            <div className="grid gap-2 sm:grid-cols-[1fr_auto_auto]">
                              <label className="grid gap-1 text-xs font-bold uppercase text-ink-500">
                                Quantity
                                <input type="number" min="1" step="1" value={quantityDrafts[item.id] ?? "1"} onChange={(event) => setQuantityDrafts((current) => ({ ...current, [item.id]: event.target.value }))} className="border border-ink-200 px-3 py-2 text-sm font-normal text-ink-900" />
                              </label>
                              <button type="button" onClick={() => void adjustQuantity(item, 1)} disabled={mutating === `quantity-${item.id}`} className="self-end border border-ink-900 px-3 py-2 text-xs font-bold hover:bg-ink-900 hover:text-white disabled:cursor-not-allowed disabled:opacity-60">
                                Add
                              </button>
                              <button type="button" onClick={() => void adjustQuantity(item, -1)} disabled={mutating === `quantity-${item.id}`} className="self-end border border-market-red/40 px-3 py-2 text-xs font-bold text-market-red hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60">
                                Remove
                              </button>
                            </div>
                            <p className="text-xs font-semibold text-ink-500">{formatCount(item.available_quantity)} currently available</p>
                            <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
                              <select value={statusDrafts[item.id] ?? item.status} onChange={(event) => setStatusDrafts((current) => ({ ...current, [item.id]: event.target.value as ListingStatus }))} className="border border-ink-200 px-3 py-2 text-sm">
                                <option value="active">Active</option>
                                <option value="sold">Sold</option>
                                <option value="cancelled">Cancelled</option>
                              </select>
                              <button type="button" onClick={() => void updateInventoryStatus(item)} disabled={mutating === `status-${item.id}`} className="border border-ink-900 px-3 py-2 text-xs font-bold hover:bg-ink-900 hover:text-white disabled:cursor-not-allowed disabled:opacity-60">
                                Set Status
                              </button>
                            </div>
                          </div>
                        ))
                      )}
                    </>
                  ) : (
                    <p className="border border-ink-200 bg-ink-50 px-3 py-2 text-sm font-semibold text-ink-600">Supreme admin required.</p>
                  )}
                </div>
              </div>
            )}
          </aside>
        </div>
      )}
    </section>
  );
}
