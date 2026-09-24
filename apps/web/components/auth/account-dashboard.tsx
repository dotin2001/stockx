"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { api, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { Cart, CartItem, ListingPage, WatchlistItem } from "@/lib/types";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";

function cartWithItems(items: CartItem[]): Cart {
  return {
    items,
    total_quantity: items.reduce((total, item) => total + item.quantity, 0)
  };
}

export function AccountDashboard() {
  const { user, accessToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [listings, setListings] = useState<ListingPage | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [cart, setCart] = useState<Cart | null>(null);
  const [mutating, setMutating] = useState<string | null>(null);
  const [checkoutVisible, setCheckoutVisible] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setCheckoutVisible(params.get("checkout") === "1");
  }, []);

  useEffect(() => {
    if (!accessToken) {
      return;
    }
    let active = true;
    setLoading(true);
    Promise.all([api.listMyListings(accessToken), api.listWatchlist(accessToken), api.getCart(accessToken)])
      .then(([listingData, watchData, cartData]) => {
        if (active) {
          setListings(listingData);
          setWatchlist(watchData);
          setCart(cartData);
          setError(null);
        }
      })
      .catch((caught: unknown) => {
        if (active) {
          setError(caught instanceof Error ? caught.message : "Could not load account data.");
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
  }, [accessToken]);

  async function updateCartQuantity(item: CartItem, quantity: number) {
    if (!accessToken || quantity < 1) {
      return;
    }
    setMutating(`cart-${item.id}`);
    setMutationError(null);
    try {
      const updated = await api.updateCartItem(accessToken, item.id, quantity);
      setCart((current) => {
        if (!current) {
          return current;
        }
        return cartWithItems(current.items.map((cartItem) => (cartItem.id === updated.id ? updated : cartItem)));
      });
    } catch (caught) {
      setMutationError(caught instanceof ApiError ? caught.message : "Could not update cart.");
    } finally {
      setMutating(null);
    }
  }

  async function removeCartItem(item: CartItem) {
    if (!accessToken) {
      return;
    }
    setMutating(`cart-${item.id}`);
    setMutationError(null);
    try {
      await api.removeCartItem(accessToken, item.id);
      setCart((current) => {
        if (!current) {
          return current;
        }
        return cartWithItems(current.items.filter((cartItem) => cartItem.id !== item.id));
      });
    } catch (caught) {
      setMutationError(caught instanceof ApiError ? caught.message : "Could not remove cart item.");
    } finally {
      setMutating(null);
    }
  }

  async function removeWatchlistItem(item: WatchlistItem) {
    if (!accessToken) {
      return;
    }
    setMutating(`watch-${item.id}`);
    setMutationError(null);
    try {
      await api.removeWatchlist(accessToken, item.id);
      setWatchlist((current) => current.filter((watchItem) => watchItem.id !== item.id));
    } catch (caught) {
      setMutationError(caught instanceof ApiError ? caught.message : "Could not remove watched product.");
    } finally {
      setMutating(null);
    }
  }

  if (loading) {
    return <LoadingState label="Loading account..." />;
  }

  if (error) {
    return <ErrorState title="Could not load account" message={error} href="/account" action="Try again" />;
  }

  return (
    <div className="grid gap-6">
      <section className="surface p-6">
        <p className="text-sm font-bold uppercase tracking-wide text-market-green">Account</p>
        <h1 className="mt-2 text-3xl font-black">{user?.name}</h1>
        <p className="mt-1 text-sm text-ink-500">{user?.email}</p>
      </section>
      {mutationError ? (
        <p className="border border-market-red/30 bg-red-50 px-3 py-2 text-sm font-semibold text-market-red">{mutationError}</p>
      ) : null}
      <div className="grid gap-6 lg:grid-cols-3">
        <section className="surface p-5">
          <h2 className="text-lg font-black">Listings</h2>
          {listings && listings.items.length > 0 ? (
            <div className="mt-4 grid gap-3">
              {listings.items.map((listing) => (
                <Link key={listing.id} href={`/product/${listing.product.slug}`} className="border border-ink-200 p-3 text-sm hover:border-market-green">
                  <strong>{listing.product.name}</strong>
                  <span className="mt-1 block text-ink-500">{listing.status}</span>
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState title="No listings yet" message="Create a listing from the sell page." href="/sell" action="Sell an item" />
          )}
        </section>
        <section className="surface p-5">
          <h2 className="text-lg font-black">Watchlist</h2>
          {watchlist.length > 0 ? (
            <div className="mt-4 grid gap-3">
              {watchlist.map((item) => (
                <div key={item.id} className="border border-ink-200 p-3 text-sm">
                  <Link href={`/product/${item.product.slug}`} className="font-bold hover:text-market-green">
                    {item.product.name}
                  </Link>
                  <button
                    type="button"
                    onClick={() => void removeWatchlistItem(item)}
                    disabled={mutating === `watch-${item.id}`}
                    className="mt-3 border border-ink-300 px-3 py-2 text-xs font-bold text-ink-700 hover:border-market-red hover:text-market-red disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {mutating === `watch-${item.id}` ? "Removing..." : "Remove"}
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="Watchlist is empty" message="Watch a product from its detail page." href="/category/sneakers" />
          )}
        </section>
        <section id="cart" className="surface p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-black">Cart</h2>
              {cart && cart.items.length > 0 ? <p className="mt-1 text-xs text-ink-500">{cart.total_quantity} item total</p> : null}
            </div>
          </div>
          {cart && cart.items.length > 0 ? (
            <>
              <div className="mt-4 grid gap-3">
                {cart.items.map((item) => (
                  <div key={item.id} className="border border-ink-200 p-3 text-sm">
                    <Link href={`/product/${item.listing.product.slug}`} className="font-bold hover:text-market-green">
                      {item.listing.product.name}
                    </Link>
                    <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
                      <span className="text-ink-500">{formatMoney(item.listing.price_cents, item.listing.currency)}</span>
                      <div className="flex items-center border border-ink-200">
                        <button
                          type="button"
                          aria-label={`Decrease ${item.listing.product.name} quantity`}
                          onClick={() => void updateCartQuantity(item, item.quantity - 1)}
                          disabled={item.quantity <= 1 || mutating === `cart-${item.id}`}
                          className="h-9 w-9 text-base font-black hover:bg-ink-100 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          -
                        </button>
                        <span className="grid h-9 min-w-10 place-items-center border-x border-ink-200 px-3 text-sm font-bold">{item.quantity}</span>
                        <button
                          type="button"
                          aria-label={`Increase ${item.listing.product.name} quantity`}
                          onClick={() => void updateCartQuantity(item, item.quantity + 1)}
                          disabled={mutating === `cart-${item.id}`}
                          className="h-9 w-9 text-base font-black hover:bg-ink-100 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          +
                        </button>
                      </div>
                    </div>
                    {!item.available ? <p className="mt-2 text-xs font-semibold text-market-red">Unavailable: {item.unavailable_reason}</p> : null}
                    <button
                      type="button"
                      onClick={() => void removeCartItem(item)}
                      disabled={mutating === `cart-${item.id}`}
                      className="mt-3 border border-ink-300 px-3 py-2 text-xs font-bold text-ink-700 hover:border-market-red hover:text-market-red disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {mutating === `cart-${item.id}` ? "Updating..." : "Remove"}
                    </button>
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={() => setCheckoutVisible(true)}
                className="mt-4 w-full bg-ink-900 px-4 py-3 text-sm font-bold text-white hover:bg-market-green"
              >
                Checkout
              </button>
              {checkoutVisible ? (
                <p className="mt-3 border border-market-green/30 bg-market-mint px-3 py-2 text-sm font-semibold text-ink-800">
                  Checkout is not available yet. Your cart is saved while payment, orders, and fulfillment are being built.
                </p>
              ) : null}
            </>
          ) : (
            <EmptyState title="Cart is empty" message="Add active listings when sellers publish products." href="/category/sneakers" />
          )}
        </section>
      </div>
    </div>
  );
}
