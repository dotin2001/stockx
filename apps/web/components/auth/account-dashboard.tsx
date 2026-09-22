"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/auth-context";
import { api } from "@/lib/api";
import type { Cart, ListingPage, WatchlistItem } from "@/lib/types";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/states";

export function AccountDashboard() {
  const { user, accessToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [listings, setListings] = useState<ListingPage | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [cart, setCart] = useState<Cart | null>(null);

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
                <Link key={item.id} href={`/product/${item.product.slug}`} className="border border-ink-200 p-3 text-sm hover:border-market-green">
                  {item.product.name}
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState title="Watchlist is empty" message="Watch a product from its detail page." href="/category/sneakers" />
          )}
        </section>
        <section className="surface p-5">
          <h2 className="text-lg font-black">Cart</h2>
          {cart && cart.items.length > 0 ? (
            <div className="mt-4 grid gap-3">
              {cart.items.map((item) => (
                <div key={item.id} className="border border-ink-200 p-3 text-sm">
                  <strong>{item.listing.product.name}</strong>
                  <span className="mt-1 block text-ink-500">Qty {item.quantity}</span>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="Cart is empty" message="Add active listings when sellers publish products." href="/category/sneakers" />
          )}
        </section>
      </div>
    </div>
  );
}
