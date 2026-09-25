export type UUID = string;

export type ApiErrorEnvelope = {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
};

export type Category = {
  id: UUID;
  name: string;
  slug: string;
  description: string | null;
};

export type ProductVariant = {
  id: UUID;
  size: string | null;
  color: string | null;
  sku: string | null;
};

export type ActiveListingSummary = {
  id: UUID;
  price_cents: number;
  currency: string;
  status: "active" | "sold" | "cancelled";
  product_variant_id: UUID | null;
  created_at: string;
};

export type ProductSummary = {
  id: UUID;
  name: string;
  slug: string;
  brand: string | null;
  image_url: string | null;
  lowest_ask_cents: number | null;
  total_sold: number;
  category: Category;
  created_at: string;
  updated_at: string;
};

export type ProductDetail = ProductSummary & {
  description: string | null;
  variants: ProductVariant[];
  lowest_active_listing: ActiveListingSummary | null;
};

export type ProductPage = {
  items: ProductSummary[];
  total: number;
  limit: number;
  offset: number;
};

export type AdminProductRead = ProductDetail & {
  archived_at: string | null;
  archived_by_user_id: UUID | null;
};

export type AdminProductPage = {
  items: AdminProductRead[];
  total: number;
  limit: number;
  offset: number;
};

export type AdminProductCreatePayload = {
  category_id: UUID;
  name: string;
  slug: string;
  brand?: string | null;
  description?: string | null;
  image_url?: string | null;
  lowest_ask_cents?: number | null;
  total_sold?: number;
};

export type ProductVariantCreatePayload = {
  size?: string | null;
  color?: string | null;
  sku?: string | null;
};

export type UserPublic = {
  id: UUID;
  name: string;
  email: string;
  is_admin: boolean;
  is_seller: boolean;
  created_at: string;
  updated_at: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  user: UserPublic;
};

export type RegisterPayload = {
  name: string;
  email: string;
  password: string;
};

export type LoginPayload = {
  email: string;
  password: string;
};

export type ListingCreatePayload = {
  product_id: UUID;
  product_variant_id?: UUID | null;
  price_cents: number;
  currency: string;
};

export type ListingRead = {
  id: UUID;
  user_id: UUID;
  product_id: UUID;
  product_variant_id: UUID | null;
  price_cents: number;
  currency: string;
  status: "active" | "sold" | "cancelled";
  created_at: string;
  updated_at: string;
};

export type ListingManagementRead = ListingRead & {
  product: ProductSummary;
};

export type ListingPage = {
  items: ListingManagementRead[];
  total: number;
  limit: number;
  offset: number;
};

export type WatchlistItem = {
  id: UUID;
  product: ProductSummary;
  created_at: string;
};

export type CartListing = {
  id: UUID;
  price_cents: number;
  currency: string;
  status: string;
  product: ProductSummary;
};

export type CartItem = {
  id: UUID;
  listing_id: UUID;
  quantity: number;
  available: boolean;
  unavailable_reason: string | null;
  listing: CartListing;
  created_at: string;
  updated_at: string;
};

export type Cart = {
  items: CartItem[];
  total_quantity: number;
};

export type SellerProfile = {
  id: UUID;
  user_id: UUID;
  phone_number: string;
  address_line1: string;
  address_line2: string | null;
  city: string;
  state: string | null;
  postal_code: string | null;
  country: string;
  created_at: string;
  updated_at: string;
};

export type SellerProfilePayload = {
  phone_number: string;
  address_line1: string;
  address_line2?: string | null;
  city: string;
  state?: string | null;
  postal_code?: string | null;
  country: string;
};

export type GuestCartItemInput = {
  listing_id: UUID;
  quantity: number;
};

export type GuestCartResolvedItem = {
  listing_id: UUID;
  quantity: number;
  available: boolean;
  unavailable_reason: string | null;
  listing: CartListing | null;
};

export type GuestCartSkippedItem = {
  listing_id: UUID;
  quantity: number;
  reason: string;
};

export type GuestCartRead = {
  items: GuestCartResolvedItem[];
  total_quantity: number;
  skipped: GuestCartSkippedItem[];
};

export type CartMergeResponse = {
  cart: Cart;
  skipped: GuestCartSkippedItem[];
};

export type CustomerMessageCreatePayload = {
  subject: string;
  body: string;
};

export type CustomerMessageRead = {
  id: UUID;
  sender_user_id: UUID;
  sender_name: string;
  sender_email: string;
  subject: string;
  body: string;
  is_read: boolean;
  read_at: string | null;
  created_at: string;
  updated_at: string;
};

export type CustomerMessagePage = {
  items: CustomerMessageRead[];
  total: number;
  limit: number;
  offset: number;
};
