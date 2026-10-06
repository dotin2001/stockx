"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import { formatCount, formatMoney } from "@/lib/format";
import { addGuestCartItem } from "@/lib/guest-cart";
import type { ProductDetail, ProductGalleryImage, ProductPurchaseOption } from "@/lib/types";
import { ProductCard } from "@/components/catalog/product-card";

function optionTone(option: ProductPurchaseOption, selected: boolean): string {
  if (selected) {
    return "border-ink-900 bg-ink-900 text-white";
  }
  if (option.is_available) {
    return "border-ink-300 bg-white text-ink-900 hover:border-market-green";
  }
  return "border-ink-200 bg-ink-50 text-ink-400";
}

function galleryForProduct(product: ProductDetail): ProductGalleryImage[] {
  const images: ProductGalleryImage[] = product.image_url ? [{ url: product.image_url, alt: product.name }] : [];
  for (const image of product.gallery_images) {
    if (!images.some((item) => item.url === image.url)) {
      images.push(image);
    }
  }
  return images;
}

export function ProductDetailView({ product }: { product: ProductDetail }) {
  const router = useRouter();
  const { status, accessToken } = useAuth();
  const [selectedOptionId, setSelectedOptionId] = useState<string | null>(product.purchase_options[0]?.id ?? null);
  const [selectedImageUrl, setSelectedImageUrl] = useState<string | null>(product.image_url);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [watching, setWatching] = useState(false);
  const [carting, setCarting] = useState<"cart" | "buy" | null>(null);

  const selectedOption = useMemo(
    () => product.purchase_options.find((option) => option.id === selectedOptionId) ?? product.purchase_options[0] ?? null,
    [product.purchase_options, selectedOptionId]
  );
  const gallery = useMemo(() => galleryForProduct(product), [product]);
  const heroImage = selectedImageUrl ?? gallery[0]?.url ?? null;
  const displayPrice = selectedOption?.price_cents ?? product.store_price_cents ?? product.lowest_ask_cents;
  const hasStock = Boolean(selectedOption?.is_available);

  async function addToWatchlist() {
    if (!accessToken) {
      return;
    }
    setWatching(true);
    setActionMessage(null);
    try {
      await api.addWatchlist(accessToken, product.id);
      setActionMessage("Added to your watchlist.");
    } catch (error) {
      setActionMessage(error instanceof ApiError ? error.message : "Could not update watchlist.");
    } finally {
      setWatching(false);
    }
  }

  async function addSelectedOptionToCart(intent: "cart" | "buy") {
    if (!selectedOption?.is_available) {
      setActionMessage("This product is currently out of stock.");
      return;
    }
    if (status !== "authenticated" || !accessToken) {
      addGuestCartItem(selectedOption.id);
      if (intent === "buy") {
        router.push("/cart?checkout=1");
        return;
      }
      setActionMessage("Added to your cart.");
      return;
    }
    setCarting(intent);
    setActionMessage(null);
    try {
      await api.addCartItem(accessToken, selectedOption.id);
      if (intent === "buy") {
        router.push("/account?checkout=1#cart");
        return;
      }
      setActionMessage("Added to your cart.");
    } catch (error) {
      setActionMessage(error instanceof ApiError ? error.message : "Could not update cart.");
    } finally {
      setCarting(null);
    }
  }

  return (
    <div className="grid gap-10">
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_420px]">
        <section className="grid gap-4">
          <div className="surface grid place-items-center bg-white p-8">
            {heroImage ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={heroImage} alt={product.name} className="max-h-[460px] object-contain" />
            ) : (
              <div className="grid h-64 w-full place-items-center bg-ink-100 text-sm font-bold uppercase text-ink-500">No image</div>
            )}
          </div>
          {gallery.length > 1 ? (
            <div className="grid grid-cols-4 gap-3 sm:grid-cols-6">
              {gallery.map((image) => (
                <button
                  key={image.url}
                  type="button"
                  onClick={() => setSelectedImageUrl(image.url)}
                  className={`surface grid aspect-square place-items-center bg-white p-2 ${heroImage === image.url ? "ring-2 ring-market-green" : ""}`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={image.url} alt={image.alt ?? product.name} className="max-h-full object-contain" />
                </button>
              ))}
            </div>
          ) : null}
        </section>

        <aside className="surface p-6">
          <p className="text-sm font-bold uppercase tracking-wide text-market-green">{product.brand ?? product.category.name}</p>
          <h1 className="mt-3 text-3xl font-black leading-tight">{product.name}</h1>
          <p className="mt-4 text-sm leading-6 text-ink-500">{product.description ?? "Verified store product."}</p>
          <div className="mt-8 grid grid-cols-2 gap-3 border-y border-ink-200 py-5">
            <div>
              <p className="text-xs text-ink-500">Store Price</p>
              <p className="text-2xl font-black">{formatMoney(displayPrice, selectedOption?.currency ?? "USD")}</p>
            </div>
            <div>
              <p className="text-xs text-ink-500">Availability</p>
              <p className="text-2xl font-black">{hasStock ? "In Stock" : "Out"}</p>
            </div>
          </div>

          {product.purchase_options.length > 0 ? (
            <div className="mt-6">
              <h2 className="text-sm font-bold uppercase tracking-wide">Select Size</h2>
              <div className="mt-3 grid grid-cols-2 gap-2">
                {product.purchase_options.map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => setSelectedOptionId(option.id)}
                    disabled={!option.is_available}
                    className={`min-h-14 border px-3 py-2 text-left text-sm font-bold disabled:cursor-not-allowed ${optionTone(option, option.id === selectedOption?.id)}`}
                  >
                    <span className="block truncate">{option.label}</span>
                    <span className="block text-xs font-semibold opacity-75">{formatMoney(option.price_cents, option.currency)}</span>
                  </button>
                ))}
              </div>
              {selectedOption ? (
                <p className="mt-3 text-xs font-semibold text-ink-500">
                  {formatCount(selectedOption.available_quantity)} available for {selectedOption.label}
                </p>
              ) : null}
            </div>
          ) : (
            <p className="mt-6 border border-ink-200 bg-ink-50 px-3 py-2 text-sm font-semibold text-ink-600">
              This product is currently out of stock.
            </p>
          )}

          <div className="mt-8 grid gap-3">
            <div className="grid gap-3 sm:grid-cols-2">
              <button
                type="button"
                onClick={() => void addSelectedOptionToCart("cart")}
                disabled={!hasStock || carting !== null}
                className="bg-market-green px-5 py-3 text-sm font-bold text-white hover:bg-ink-900 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {carting === "cart" ? "Adding..." : "Add to Cart"}
              </button>
              <button
                type="button"
                onClick={() => void addSelectedOptionToCart("buy")}
                disabled={!hasStock || carting !== null}
                className="bg-ink-900 px-5 py-3 text-sm font-bold text-white hover:bg-market-green disabled:cursor-not-allowed disabled:opacity-60"
              >
                {carting === "buy" ? "Starting..." : "Buy Now"}
              </button>
            </div>
            {status === "authenticated" ? (
              <button type="button" onClick={addToWatchlist} disabled={watching} className="border border-ink-900 px-5 py-3 text-sm font-bold text-ink-900 hover:bg-ink-900 hover:text-white disabled:cursor-not-allowed disabled:opacity-60">
                {watching ? "Adding..." : "Add to Watchlist"}
              </button>
            ) : null}
            {actionMessage ? <p className="text-sm font-semibold text-ink-600">{actionMessage}</p> : null}
          </div>
        </aside>
      </div>

      {product.feature_bullets.length > 0 || product.detail_rows.length > 0 || product.stats ? (
        <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
          {product.feature_bullets.length > 0 || product.detail_rows.length > 0 ? (
            <div className="surface p-6">
              <h2 className="text-xl font-black">Product Details</h2>
              {product.feature_bullets.length > 0 ? (
                <ul className="mt-4 grid gap-3 text-sm font-semibold text-ink-700">
                  {product.feature_bullets.map((feature) => (
                    <li key={feature} className="border-b border-ink-100 pb-3 last:border-0 last:pb-0">
                      {feature}
                    </li>
                  ))}
                </ul>
              ) : null}
              {product.detail_rows.length > 0 ? (
                <dl className="mt-5 grid gap-3 text-sm">
                  {product.detail_rows.map((row) => (
                    <div key={`${row.label}-${row.value}`} className="grid grid-cols-[130px_1fr] gap-4 border-t border-ink-100 pt-3">
                      <dt className="font-bold text-ink-500">{row.label}</dt>
                      <dd className="font-semibold text-ink-900">{row.value}</dd>
                    </div>
                  ))}
                </dl>
              ) : null}
            </div>
          ) : null}

          {product.stats ? (
            <div className="surface p-6">
              <h2 className="text-xl font-black">Product Stats</h2>
              <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-xs text-ink-500">Sold</dt>
                  <dd className="text-lg font-black">{formatCount(product.stats.total_sold)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-500">Sizes</dt>
                  <dd className="text-lg font-black">{formatCount(product.stats.available_size_count)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-500">Stock</dt>
                  <dd className="text-lg font-black">{formatCount(product.stats.total_available_quantity)}</dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-500">Category</dt>
                  <dd className="text-lg font-black">{product.stats.category}</dd>
                </div>
              </dl>
            </div>
          ) : null}
        </section>
      ) : null}

      {product.related_products.length > 0 ? (
        <section>
          <h2 className="text-2xl font-black">Related Products</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {product.related_products.map((relatedProduct) => (
              <ProductCard key={relatedProduct.id} product={relatedProduct} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
