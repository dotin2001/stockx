import type {
  ApiErrorEnvelope,
  AuthResponse,
  Cart,
  Category,
  ListingCreatePayload,
  ListingPage,
  ListingRead,
  LoginPayload,
  ProductDetail,
  ProductPage,
  RegisterPayload,
  UserPublic,
  UUID,
  WatchlistItem
} from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

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
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  accessToken?: string | null;
  credentials?: RequestCredentials;
  cache?: RequestCache;
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

  const response = await fetch(`${API_BASE_URL}${path}`, {
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

export const api = {
  listCategories: () => apiRequest<Category[]>("/api/v1/categories"),
  listProducts: (limit = 20, offset = 0) => apiRequest<ProductPage>(`/api/v1/products?limit=${limit}&offset=${offset}`),
  listCategoryProducts: (slug: string, limit = 20, offset = 0) =>
    apiRequest<ProductPage>(`/api/v1/categories/${encodeURIComponent(slug)}/products?limit=${limit}&offset=${offset}`),
  getProduct: (slug: string) => apiRequest<ProductDetail>(`/api/v1/products/${encodeURIComponent(slug)}`),
  searchProducts: (query: string, limit = 20, offset = 0) =>
    apiRequest<ProductPage>(
      `/api/v1/search?q=${encodeURIComponent(query)}&limit=${limit}&offset=${offset}`
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
  addCartItem: (accessToken: string, listingId: UUID, quantity = 1) =>
    apiRequest<Cart["items"][number]>("/api/v1/cart/items", {
      method: "POST",
      body: { listing_id: listingId, quantity },
      accessToken
    })
};

export function getApiBaseUrl() {
  return API_BASE_URL;
}
