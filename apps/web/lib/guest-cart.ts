import type { UUID } from "@/lib/types";

export type GuestCartItem = {
  listing_id: UUID;
  quantity: number;
};

export const GUEST_CART_STORAGE_KEY = "stockx:guest-cart:v1";
export const CART_MERGE_NOTICE_KEY = "stockx:cart-merge-notice:v1";

function safeRead(): GuestCartItem[] {
  if (typeof window === "undefined") {
    return [];
  }
  try {
    const raw = window.localStorage.getItem(GUEST_CART_STORAGE_KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed
      .filter((item): item is GuestCartItem => {
        if (!item || typeof item !== "object") {
          return false;
        }
        const candidate = item as Partial<GuestCartItem>;
        return typeof candidate.listing_id === "string" && typeof candidate.quantity === "number" && Number.isInteger(candidate.quantity) && candidate.quantity > 0;
      })
      .map((item) => ({ listing_id: item.listing_id, quantity: item.quantity }));
  } catch {
    return [];
  }
}

function write(items: GuestCartItem[]) {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(GUEST_CART_STORAGE_KEY, JSON.stringify(items));
  window.dispatchEvent(new Event("stockx:guest-cart-updated"));
}

export function getGuestCartItems() {
  return safeRead();
}

export function getGuestCartTotalQuantity() {
  return safeRead().reduce((total, item) => total + item.quantity, 0);
}

export function addGuestCartItem(listingId: UUID, quantity = 1) {
  const items = safeRead();
  const existing = items.find((item) => item.listing_id === listingId);
  if (existing) {
    existing.quantity += quantity;
  } else {
    items.push({ listing_id: listingId, quantity });
  }
  write(items);
  return items;
}

export function updateGuestCartItem(listingId: UUID, quantity: number) {
  if (quantity < 1) {
    return safeRead();
  }
  const items = safeRead().map((item) => (item.listing_id === listingId ? { ...item, quantity } : item));
  write(items);
  return items;
}

export function removeGuestCartItem(listingId: UUID) {
  const items = safeRead().filter((item) => item.listing_id !== listingId);
  write(items);
  return items;
}

export function clearGuestCart() {
  write([]);
}

export function rememberCartMergeNotice(message: string) {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(CART_MERGE_NOTICE_KEY, message);
}

export function consumeCartMergeNotice() {
  if (typeof window === "undefined") {
    return null;
  }
  const message = window.sessionStorage.getItem(CART_MERGE_NOTICE_KEY);
  if (message) {
    window.sessionStorage.removeItem(CART_MERGE_NOTICE_KEY);
  }
  return message;
}
