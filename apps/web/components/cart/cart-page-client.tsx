"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { getGuestCartItems, removeGuestCartItem, updateGuestCartItem } from "@/lib/guest-cart";
import type { Cart, CartItem, GuestCartRead, UUID } from "@/lib/types";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";

function cartWithItems(items: CartItem[]): Cart {
  return {
    items,
    total_quantity: items.reduce((total, item) => total + item.quantity, 0)
  };
}

function authRedirect() {
  return `/login?redirect=${encodeURIComponent("/account?checkout=1#cart")}`;
}

export function CartPageClient() {
  const router = useRouter();
  const params = useSearchParams();
  const { status, accessToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cart, setCart] = useState<Cart | null>(null);
  const [guestCart, setGuestCart] = useState<GuestCartRead | null>(null);
  const [checkoutVisible, setCheckoutVisible] = useState(params.get("checkout") === "1");
  const [mutating, setMutating] = useState<string | null>(null);

  const loadGuestCart = useCallback(async () => {
    const items = getGuestCartItems();
    if (items.length === 0) {
      setGuestCart({ items: [], total_quantity: 0, skipped: [] });
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      setGuestCart(await api.resolveGuestCart(items));
      setError(null);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Could not load cart.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (status === "checking") {
      return;
    }
    let active = true;
    setLoading(true);
    if (status === "authenticated" && accessToken) {
      api
        .getCart(accessToken)
        .then((data) => {
          if (active) {
            setCart(data);
            setError(null);
          }
        })
        .catch((caught: unknown) => {
          if (active) {
            setError(caught instanceof ApiError ? caught.message : "Could not load cart.");
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
    }
    void loadGuestCart();
    return () => {
      active = false;
    };
  }, [accessToken, loadGuestCart, status]);

  async function updateAuthQuantity(item: CartItem, quantity: number) {
    if (!accessToken || quantity < 1) {
      return;
    }
    setMutating(item.id);
    try {
      const updated = await api.updateCartItem(accessToken, item.id, quantity);
      setCart((current) => (current ? cartWithItems(current.items.map((cartItem) => (cartItem.id === updated.id ? updated : cartItem))) : current));
    } finally {
      setMutating(null);
    }
  }

  async function removeAuthItem(item: CartItem) {
    if (!accessToken) {
      return;
    }
    setMutating(item.id);
    try {
      await api.removeCartItem(accessToken, item.id);
      setCart((current) => (current ? cartWithItems(current.items.filter((cartItem) => cartItem.id !== item.id)) : current));
    } finally {
      setMutating(null);
    }
  }

  function updateGuestQuantity(listingId: UUID, quantity: number) {
    updateGuestCartItem(listingId, quantity);
    void loadGuestCart();
  }

  function removeGuestItem(listingId: UUID) {
    removeGuestCartItem(listingId);
    void loadGuestCart();
  }

  function checkout() {
    if (status !== "authenticated") {
      router.push(authRedirect());
      return;
    }
    setCheckoutVisible(true);
  }

  if (status === "checking" || loading) {
    return <LoadingState label="Loading cart..." />;
  }

  if (error) {
    return <ErrorState title="Could not load cart" message={error} href="/cart" action="Try again" />;
  }

  const isAuthenticated = status === "authenticated";
  const authItems = cart?.items ?? [];
  const guestItems = guestCart?.items ?? [];
  const hasItems = isAuthenticated ? authItems.length > 0 : guestItems.length > 0;
  const totalQuantity = isAuthenticated ? cart?.total_quantity ?? 0 : guestCart?.total_quantity ?? 0;

  return (
    <section className="surface mx-auto grid max-w-3xl gap-5 p-6">
      <div>
        <p className="text-sm font-bold uppercase tracking-wide text-market-green">Cart</p>
        <h1 className="mt-2 text-3xl font-black">{isAuthenticated ? "Account cart" : "Guest cart"}</h1>
        {hasItems ? <p className="mt-2 text-sm text-ink-500">{totalQuantity} available item total</p> : null}
      </div>

      {!hasItems ? (
        <EmptyState title="Cart is empty" message="Add active listings from product pages." href="/category/sneakers" action="Browse products" />
      ) : (
        <>
          <div className="grid gap-3">
            {isAuthenticated
              ? authItems.map((item) => (
                  <div key={item.id} className="border border-ink-200 p-4 text-sm">
                    <CartLine
                      name={item.listing.product.name}
                      href={`/product/${item.listing.product.slug}`}
                      price={formatMoney(item.listing.price_cents, item.listing.currency)}
                      quantity={item.quantity}
                      available={item.available}
                      unavailableReason={item.unavailable_reason}
                      disabled={mutating === item.id}
                      onDecrease={() => void updateAuthQuantity(item, item.quantity - 1)}
                      onIncrease={() => void updateAuthQuantity(item, item.quantity + 1)}
                      onRemove={() => void removeAuthItem(item)}
                    />
                  </div>
                ))
              : guestItems.map((item) => (
                  <div key={item.listing_id} className="border border-ink-200 p-4 text-sm">
                    <CartLine
                      name={item.listing?.product.name ?? "Unavailable listing"}
                      href={item.listing ? `/product/${item.listing.product.slug}` : undefined}
                      price={item.listing ? formatMoney(item.listing.price_cents, item.listing.currency) : "Unavailable"}
                      quantity={item.quantity}
                      available={item.available}
                      unavailableReason={item.unavailable_reason}
                      disabled={mutating === item.listing_id}
                      onDecrease={() => updateGuestQuantity(item.listing_id, item.quantity - 1)}
                      onIncrease={() => updateGuestQuantity(item.listing_id, item.quantity + 1)}
                      onRemove={() => removeGuestItem(item.listing_id)}
                    />
                  </div>
                ))}
          </div>
          <button type="button" onClick={checkout} className="bg-ink-900 px-4 py-3 text-sm font-bold text-white hover:bg-market-green">
            Checkout
          </button>
          {!isAuthenticated ? (
            <p className="border border-ink-200 bg-ink-50 px-3 py-2 text-sm font-semibold text-ink-600">Login or sign up to continue checkout. Your cart will move into your account.</p>
          ) : null}
          {checkoutVisible && isAuthenticated ? (
            <p className="border border-market-green/30 bg-market-mint px-3 py-2 text-sm font-semibold text-ink-800">
              Checkout is not available yet. Your cart is saved while payment, orders, and fulfillment are being built.
            </p>
          ) : null}
        </>
      )}
    </section>
  );
}

function CartLine({
  name,
  href,
  price,
  quantity,
  available,
  unavailableReason,
  disabled,
  onDecrease,
  onIncrease,
  onRemove
}: {
  name: string;
  href?: string;
  price: string;
  quantity: number;
  available: boolean;
  unavailableReason: string | null;
  disabled: boolean;
  onDecrease: () => void;
  onIncrease: () => void;
  onRemove: () => void;
}) {
  const title = href ? (
    <Link href={href} className="font-bold hover:text-market-green">
      {name}
    </Link>
  ) : (
    <strong>{name}</strong>
  );

  return (
    <div>
      {title}
      <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
        <span className="text-ink-500">{price}</span>
        <div className="flex items-center border border-ink-200">
          <button type="button" aria-label={`Decrease ${name} quantity`} onClick={onDecrease} disabled={quantity <= 1 || disabled} className="h-9 w-9 text-base font-black hover:bg-ink-100 disabled:cursor-not-allowed disabled:opacity-40">
            -
          </button>
          <span className="grid h-9 min-w-10 place-items-center border-x border-ink-200 px-3 text-sm font-bold">{quantity}</span>
          <button type="button" aria-label={`Increase ${name} quantity`} onClick={onIncrease} disabled={disabled} className="h-9 w-9 text-base font-black hover:bg-ink-100 disabled:cursor-not-allowed disabled:opacity-40">
            +
          </button>
        </div>
      </div>
      {!available ? <p className="mt-2 text-xs font-semibold text-market-red">Unavailable: {unavailableReason}</p> : null}
      <button type="button" onClick={onRemove} disabled={disabled} className="mt-3 border border-ink-300 px-3 py-2 text-xs font-bold text-ink-700 hover:border-market-red hover:text-market-red disabled:cursor-not-allowed disabled:opacity-60">
        Remove
      </button>
    </div>
  );
}
