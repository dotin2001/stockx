import type {
  ApiErrorEnvelope,
  AdminOrderPage,
  AdminOrderQuery,
  AdminListingCreatePayload,
  AdminListingInventoryUpdatePayload,
  AdminProductCreatePayload,
  AdminProductPage,
  AdminProductRead,
  AdminProductUpdatePayload,
  AdminUserPage,
  AdminUserPromoteByEmailPayload,
  AdminUserRead,
  AuthResponse,
  Cart,
  CartMergeResponse,
  CheckoutSummary,
  Category,
  CustomerMessageCreatePayload,
  CustomerMessagePage,
  CustomerMessageRead,
  GuestCartItemInput,
  GuestCartRead,
  ListingCreatePayload,
  ListingManagementRead,
  ListingQuantityAdjustmentPayload,
  ListingPage,
  ListingRead,
  ListingStatusUpdatePayload,
  LoginPayload,
  Order,
  OrderCreatePayload,
  OrderPage,
  PaymentCancellation,
  PaymentSession,
  ProductDetail,
  ProductDiscoveryQueryParams,
  ProductPage,
  ProductVariant,
  ProductVariantCreatePayload,
  ProductVariantUpdatePayload,
  RegisterPayload,
  SellerProfile,
  SellerProfilePayload,
  UserPublic,
  UUID,
  WatchlistItem
} from "@/lib/types";

const CONFIGURED_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;

function resolveApiBaseUrl() {
  if (CONFIGURED_API_BASE_URL) return CONFIGURED_API_BASE_URL;

  // Keep the API and frontend on the same hostname in local development.
  // This lets the browser send the HTTP-only refresh cookie after returning
  // from a full-page redirect such as Stripe Checkout.
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }

  return "http://localhost:8000";
}

export class ApiError extends Error {
  code: string;
  status: number;
  details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  accessToken?: string | null;
  credentials?: RequestCredentials;
  cache?: RequestCache;
  headers?: Record<string, string>;
};

async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers();
  headers.set("Accept", "application/json");

  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (options.accessToken) {
    headers.set("Authorization", `Bearer ${options.accessToken}`);
  }
  for (const [name, value] of Object.entries(options.headers ?? {})) {
    headers.set(name, value);
  }

  const response = await fetch(`${resolveApiBaseUrl()}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    credentials: options.credentials,
    cache: options.cache ?? "no-store"
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const json = (await response.json().catch(() => null)) as unknown;
  if (!response.ok) {
    if (json && typeof json === "object" && "error" in json) {
      const error = (json as Partial<ApiErrorEnvelope>).error;
      throw new ApiError(
        response.status,
        error?.code ?? "api_error",
        error?.message ?? "Request failed.",
        error?.details
      );
    }
    throw new ApiError(response.status, "api_error", "Request failed.");
  }

  return json as T;
}

function productDiscoverySearchParams(limit: number, offset: number, params: ProductDiscoveryQueryParams = {}) {
  const searchParams = new URLSearchParams({
    limit: String(params.limit ?? limit),
    offset: String(params.offset ?? offset)
  });
  if (params.q) {
    searchParams.set("q", params.q);
  }
  for (const brand of params.brand ?? []) {
    searchParams.append("brand", brand);
  }
  for (const size of params.size ?? []) {
    searchParams.append("size", size);
  }
  if (params.min_price !== undefined && params.min_price !== null) {
    searchParams.set("min_price", String(params.min_price));
  }
  if (params.max_price !== undefined && params.max_price !== null) {
    searchParams.set("max_price", String(params.max_price));
  }
  if (params.available_only) {
    searchParams.set("available_only", "true");
  }
  if (params.sort) {
    searchParams.set("sort", params.sort);
  }
  return searchParams;
}

function adminOrderSearchParams(query: AdminOrderQuery) {
  const params = new URLSearchParams();
  if (query.search !== undefined) params.set("search", query.search);
  if (query.status !== undefined) params.set("status", query.status);
  if (query.payment_status !== undefined) params.set("payment_status", query.payment_status);
  if (query.limit !== undefined) params.set("limit", String(query.limit));
  if (query.offset !== undefined) params.set("offset", String(query.offset));
  return params;
}

export const api = {
  listCategories: () => apiRequest<Category[]>("/api/v1/categories"),
  listProducts: (limit = 20, offset = 0, params: ProductDiscoveryQueryParams = {}) =>
    apiRequest<ProductPage>(`/api/v1/products?${productDiscoverySearchParams(limit, offset, params).toString()}`),
  listCategoryProducts: (slug: string, limit = 20, offset = 0, params: ProductDiscoveryQueryParams = {}) =>
    apiRequest<ProductPage>(
      `/api/v1/categories/${encodeURIComponent(slug)}/products?${productDiscoverySearchParams(limit, offset, params).toString()}`
    ),
  getProduct: (slug: string) => apiRequest<ProductDetail>(`/api/v1/products/${encodeURIComponent(slug)}`),
  searchProducts: (query: string, limit = 20, offset = 0, params: ProductDiscoveryQueryParams = {}) =>
    apiRequest<ProductPage>(
      `/api/v1/search?${productDiscoverySearchParams(limit, offset, { ...params, q: query }).toString()}`
    ),
  register: (payload: RegisterPayload) =>
    apiRequest<AuthResponse>("/api/v1/auth/register", {
      method: "POST",
      body: payload,
      credentials: "include"
    }),
  login: (payload: LoginPayload) =>
    apiRequest<AuthResponse>("/api/v1/auth/login", {
      method: "POST",
      body: payload,
      credentials: "include"
    }),
  refresh: () =>
    apiRequest<AuthResponse>("/api/v1/auth/refresh", {
      method: "POST",
      credentials: "include"
    }),
  me: (accessToken: string) =>
    apiRequest<UserPublic>("/api/v1/auth/me", {
      accessToken
    }),
  logout: () =>
    apiRequest<void>("/api/v1/auth/logout", {
      method: "POST",
      credentials: "include"
    }),
  listMyListings: (accessToken: string) =>
    apiRequest<ListingPage>("/api/v1/listings", {
      accessToken
    }),
  createListing: (accessToken: string, payload: ListingCreatePayload) =>
    apiRequest<ListingRead>("/api/v1/listings", {
      method: "POST",
      body: payload,
      accessToken
    }),
  getSellerProfile: (accessToken: string) =>
    apiRequest<SellerProfile>("/api/v1/seller/profile", {
      accessToken
    }),
  upsertSellerProfile: (accessToken: string, payload: SellerProfilePayload) =>
    apiRequest<SellerProfile>("/api/v1/seller/profile", {
      method: "PUT",
      body: payload,
      accessToken
    }),
  listWatchlist: (accessToken: string) =>
    apiRequest<WatchlistItem[]>("/api/v1/watchlist", {
      accessToken
    }),
  addWatchlist: (accessToken: string, productId: UUID) =>
    apiRequest<WatchlistItem>("/api/v1/watchlist", {
      method: "POST",
      body: { product_id: productId },
      accessToken
    }),
  removeWatchlist: (accessToken: string, itemId: UUID) =>
    apiRequest<void>(`/api/v1/watchlist/${itemId}`, {
      method: "DELETE",
      accessToken
    }),
  getCart: (accessToken: string) =>
    apiRequest<Cart>("/api/v1/cart", {
      accessToken
    }),
  resolveGuestCart: (items: GuestCartItemInput[]) =>
    apiRequest<GuestCartRead>("/api/v1/cart/guest/resolve", {
      method: "POST",
      body: { items }
    }),
  mergeGuestCart: (accessToken: string, items: GuestCartItemInput[]) =>
    apiRequest<CartMergeResponse>("/api/v1/cart/merge", {
      method: "POST",
      body: { items },
      accessToken
    }),
  addCartItem: (accessToken: string, listingId: UUID, quantity = 1) =>
    apiRequest<Cart["items"][number]>("/api/v1/cart/items", {
      method: "POST",
      body: { listing_id: listingId, quantity },
      accessToken
    }),
  updateCartItem: (accessToken: string, itemId: UUID, quantity: number) =>
    apiRequest<Cart["items"][number]>(`/api/v1/cart/items/${itemId}`, {
      method: "PATCH",
      body: { quantity },
      accessToken
    }),
  removeCartItem: (accessToken: string, itemId: UUID) =>
    apiRequest<void>(`/api/v1/cart/items/${itemId}`, {
      method: "DELETE",
      accessToken
    }),
  getCheckoutSummary: (accessToken: string) =>
    apiRequest<CheckoutSummary>("/api/v1/checkout/summary", {
      accessToken
    }),
  createOrder: (accessToken: string, idempotencyKey: string, payload: OrderCreatePayload) =>
    apiRequest<Order>("/api/v1/orders", {
      method: "POST",
      body: payload,
      accessToken,
      headers: { "Idempotency-Key": idempotencyKey }
    }),
  createCheckoutSession: (accessToken: string, idempotencyKey: string, payload: OrderCreatePayload) =>
    apiRequest<PaymentSession>("/api/v1/checkout/sessions", {
      method: "POST",
      body: payload,
      accessToken,
      headers: { "Idempotency-Key": idempotencyKey }
    }),
  listOrders: (accessToken: string, limit = 20, offset = 0) =>
    apiRequest<OrderPage>(`/api/v1/orders?limit=${limit}&offset=${offset}`, {
      accessToken
    }),
  getOrder: (accessToken: string, orderId: UUID) =>
    apiRequest<Order>(`/api/v1/orders/${orderId}`, {
      accessToken
    }),
  listAdminOrders: (accessToken: string, query: AdminOrderQuery = {}) => {
    const params = adminOrderSearchParams(query).toString();
    return apiRequest<AdminOrderPage>(`/api/v1/admin/orders${params ? `?${params}` : ""}`, {
      accessToken
    });
  },
  getAdminOrder: (accessToken: string, orderId: UUID) =>
    apiRequest<Order>(`/api/v1/admin/orders/${encodeURIComponent(orderId)}`, {
      accessToken
    }),
  getPaymentSession: (accessToken: string, orderId: UUID) =>
    apiRequest<PaymentSession>(`/api/v1/orders/${orderId}/payment-session`, {
      accessToken
    }),
  cancelPendingPayment: (accessToken: string, orderId: UUID) =>
    apiRequest<PaymentCancellation>(`/api/v1/orders/${orderId}/cancel-payment`, {
      method: "POST",
      accessToken
    }),
  listCustomerMessages: (accessToken: string, limit = 20, offset = 0) =>
    apiRequest<CustomerMessagePage>(`/api/v1/messages?limit=${limit}&offset=${offset}`, {
      accessToken
    }),
  createCustomerMessage: (accessToken: string, payload: CustomerMessageCreatePayload) =>
    apiRequest<CustomerMessageRead>("/api/v1/messages", {
      method: "POST",
      body: payload,
      accessToken
    }),
  listAdminCustomerMessages: (accessToken: string, limit = 20, offset = 0) =>
    apiRequest<CustomerMessagePage>(`/api/v1/admin/messages?limit=${limit}&offset=${offset}`, {
      accessToken
    }),
  markAdminCustomerMessageRead: (accessToken: string, messageId: UUID) =>
    apiRequest<CustomerMessageRead>(`/api/v1/admin/messages/${messageId}/read`, {
      method: "POST",
      accessToken
    }),
  createAdminProduct: (accessToken: string, payload: AdminProductCreatePayload) =>
    apiRequest<AdminProductRead>("/api/v1/admin/products", {
      method: "POST",
      body: payload,
      accessToken
    }),
  listAdminProducts: (accessToken: string, archived?: boolean, limit = 50, offset = 0) => {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset)
    });
    if (archived !== undefined) {
      params.set("archived", String(archived));
    }
    return apiRequest<AdminProductPage>(`/api/v1/admin/products?${params.toString()}`, {
      accessToken
    });
  },
  updateAdminProduct: (accessToken: string, productId: UUID, payload: AdminProductUpdatePayload) =>
    apiRequest<AdminProductRead>(`/api/v1/admin/products/${productId}`, {
      method: "PATCH",
      body: payload,
      accessToken
    }),
  archiveAdminProduct: (accessToken: string, productId: UUID) =>
    apiRequest<AdminProductRead>(`/api/v1/admin/products/${productId}/archive`, {
      method: "POST",
      accessToken
    }),
  restoreAdminProduct: (accessToken: string, productId: UUID) =>
    apiRequest<AdminProductRead>(`/api/v1/admin/products/${productId}/restore`, {
      method: "POST",
      accessToken
    }),
  createAdminProductListing: (accessToken: string, productId: UUID, payload: AdminListingCreatePayload) =>
    apiRequest<ListingManagementRead>(`/api/v1/admin/products/${productId}/listings`, {
      method: "POST",
      body: payload,
      accessToken
    }),
  createAdminProductVariant: (accessToken: string, productId: UUID, payload: ProductVariantCreatePayload) =>
    apiRequest<ProductVariant>(`/api/v1/admin/products/${productId}/variants`, {
      method: "POST",
      body: payload,
      accessToken
    }),
  updateAdminProductVariant: (accessToken: string, variantId: UUID, payload: ProductVariantUpdatePayload) =>
    apiRequest<ProductVariant>(`/api/v1/admin/product-variants/${variantId}`, {
      method: "PATCH",
      body: payload,
      accessToken
    }),
  deleteAdminProductVariant: (accessToken: string, variantId: UUID) =>
    apiRequest<void>(`/api/v1/admin/product-variants/${variantId}`, {
      method: "DELETE",
      accessToken
    }),
  adjustAdminListingQuantity: (accessToken: string, listingId: UUID, payload: ListingQuantityAdjustmentPayload) =>
    apiRequest<ListingManagementRead>(`/api/v1/admin/listings/${listingId}/inventory/quantity`, {
      method: "POST",
      body: payload,
      accessToken
    }),
  updateAdminListingStatus: (accessToken: string, listingId: UUID, payload: ListingStatusUpdatePayload) =>
    apiRequest<ListingManagementRead>(`/api/v1/admin/listings/${listingId}/inventory/status`, {
      method: "PATCH",
      body: payload,
      accessToken
    }),
  updateAdminListingInventory: (accessToken: string, listingId: UUID, payload: AdminListingInventoryUpdatePayload) =>
    apiRequest<ListingManagementRead>(`/api/v1/admin/listings/${listingId}/inventory`, {
      method: "PATCH",
      body: payload,
      accessToken
    }),
  listAdminUsers: (accessToken: string, search = "", limit = 20, offset = 0) => {
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(offset)
    });
    if (search.trim()) {
      params.set("search", search.trim());
    }
    return apiRequest<AdminUserPage>(`/api/v1/admin/users?${params.toString()}`, {
      accessToken
    });
  },
  promoteAdminUser: (accessToken: string, payload: AdminUserPromoteByEmailPayload) =>
    apiRequest<AdminUserRead>("/api/v1/admin/users/promote", {
      method: "POST",
      body: payload,
      accessToken
    }),
  demoteAdminUser: (accessToken: string, userId: UUID) =>
    apiRequest<AdminUserRead>(`/api/v1/admin/users/${userId}/demote`, {
      method: "POST",
      accessToken
    })
};

export function getApiBaseUrl() {
  return resolveApiBaseUrl();
}
