export type UUID = string;

export type ListingStatus = "active" | "sold" | "cancelled";

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
  available_quantity: number;
  currency: string;
  status: ListingStatus;
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
  store_price_cents: number | null;
  total_sold: number;
  category: Category;
  created_at: string;
  updated_at: string;
};

export type ProductDetailRow = {
  label: string;
  value: string;
};

export type ProductGalleryImage = {
  url: string;
  alt: string | null;
};

export type ProductPurchaseOption = {
  id: UUID;
  product_variant_id: UUID | null;
  variant: ProductVariant | null;
  label: string;
  price_cents: number;
  available_quantity: number;
  currency: string;
  status: ListingStatus;
  is_available: boolean;
};

export type ProductStats = {
  total_sold: number;
  available_size_count: number;
  total_available_quantity: number;
  stock_state: "in_stock" | "out_of_stock" | string;
  category: string;
  brand: string | null;
};

export type ProductDiscoverySort = "newest" | "price_asc" | "price_desc" | "popular" | "name_asc";

export type ProductDiscoveryQueryParams = {
  q?: string | null;
  brand?: string[];
  size?: string[];
  min_price?: number | null;
  max_price?: number | null;
  available_only?: boolean;
  sort?: ProductDiscoverySort;
  limit?: number;
  offset?: number;
};

export type ProductDiscoverySelectedFilters = {
  q: string | null;
  category_slug: string | null;
  brands: string[];
  sizes: string[];
  min_price_cents: number | null;
  max_price_cents: number | null;
  available_only: boolean;
};

export type ProductDiscoveryFacetOption = {
  value: string;
  label: string;
  count: number;
};

export type ProductDiscoveryPriceBounds = {
  min_cents: number | null;
  max_cents: number | null;
};

export type ProductDiscoveryMetadata = {
  selected: ProductDiscoverySelectedFilters;
  sort: ProductDiscoverySort;
  brands: ProductDiscoveryFacetOption[];
  sizes: ProductDiscoveryFacetOption[];
  price_bounds: ProductDiscoveryPriceBounds;
  total: number;
  limit: number;
  offset: number;
};

export type ProductDetail = ProductSummary & {
  description: string | null;
  variants: ProductVariant[];
  lowest_active_listing: ActiveListingSummary | null;
  feature_bullets: string[];
  detail_rows: ProductDetailRow[];
  gallery_images: ProductGalleryImage[];
  purchase_options: ProductPurchaseOption[];
  stats: ProductStats | null;
  related_products: ProductSummary[];
};

export type ProductPage = {
  items: ProductSummary[];
  total: number;
  limit: number;
  offset: number;
  discovery: ProductDiscoveryMetadata;
};

export type AdminProductRead = ProductDetail & {
  archived_at: string | null;
  archived_by_user_id: UUID | null;
  inventory_summary: AdminProductInventorySummary;
  inventory_items: AdminProductInventoryItem[];
};

export type AdminProductPage = {
  items: AdminProductRead[];
  total: number;
  limit: number;
  offset: number;
};

export type AdminProductInventorySummary = {
  total_listings: number;
  active_listings: number;
  total_available_quantity: number;
  lowest_active_price_cents: number | null;
};

export type AdminProductInventoryItem = {
  id: UUID;
  user_id: UUID;
  product_variant_id: UUID | null;
  variant: ProductVariant | null;
  price_cents: number;
  available_quantity: number;
  currency: string;
  status: ListingStatus;
  created_at: string;
  updated_at: string;
};

export type AdminProductCreatePayload = {
  category_id: UUID;
  name: string;
  slug: string;
  brand?: string | null;
  description?: string | null;
  image_url?: string | null;
  feature_bullets?: string[];
  detail_rows?: ProductDetailRow[];
  gallery_images?: ProductGalleryImage[];
  lowest_ask_cents?: number | null;
  total_sold?: number;
};

export type AdminProductUpdatePayload = Partial<AdminProductCreatePayload>;

export type ProductVariantCreatePayload = {
  size?: string | null;
  color?: string | null;
  sku?: string | null;
};

export type ProductVariantUpdatePayload = ProductVariantCreatePayload;

export type ListingQuantityAdjustmentPayload = {
  adjustment: number;
};

export type ListingStatusUpdatePayload = {
  status: ListingStatus;
};

export type AdminListingCreatePayload = {
  product_variant_id?: UUID | null;
  price_cents: number;
  currency: string;
  available_quantity: number;
  status: ListingStatus;
};

export type AdminListingInventoryUpdatePayload = AdminListingCreatePayload;

export type UserPublic = {
  id: UUID;
  name: string;
  email: string;
  is_admin: boolean;
  is_supreme_admin: boolean;
  is_seller: boolean;
  created_at: string;
  updated_at: string;
};

export type AuthResponse = {
  access_token: string;
  token_type: "bearer";
  user: UserPublic;
};

export type AdminUserRead = {
  id: UUID;
  name: string;
  email: string;
  is_admin: boolean;
  is_supreme_admin: boolean;
  created_at: string;
  updated_at: string;
};

export type AdminUserPage = {
  items: AdminUserRead[];
  total: number;
  limit: number;
  offset: number;
};

export type AdminUserPromoteByEmailPayload = {
  email: string;
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
  available_quantity: number;
  currency: string;
  status: ListingStatus;
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
  available_quantity: number;
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

export type CheckoutMode = "disabled" | "manual";
export type OrderStatus = "pending_payment" | "confirmed" | "cancelled";
export type PaymentStatus = "unpaid" | "paid" | "failed" | "refunded";

export type ShippingAddress = {
  recipient_name: string;
  contact_email: string;
  contact_phone: string;
  address_line1: string;
  address_line2?: string | null;
  city: string;
  state?: string | null;
  postal_code: string;
  country: string;
};

export type CheckoutItem = {
  cart_item_id: UUID;
  listing_id: UUID;
  product_id: UUID;
  product_variant_id: UUID | null;
  product_name: string;
  product_slug: string;
  product_image_url: string | null;
  variant_label: string | null;
  quantity: number;
  unit_price_cents: number;
  line_total_cents: number;
};

export type CheckoutSummary = {
  items: CheckoutItem[];
  currency: string;
  subtotal_cents: number;
  shipping_cents: number;
  tax_cents: number;
  total_cents: number;
  checkout_mode: CheckoutMode;
  order_placement_enabled: boolean;
  checkout_token: string;
};

export type OrderCreatePayload = {
  checkout_token: string;
  shipping: ShippingAddress;
};

export type OrderItem = {
  id: UUID;
  listing_id: UUID | null;
  product_id: UUID | null;
  product_variant_id: UUID | null;
  product_name: string;
  product_slug: string;
  product_image_url: string | null;
  variant_label: string | null;
  variant_sku: string | null;
  variant_size: string | null;
  variant_color: string | null;
  quantity: number;
  unit_price_cents: number;
  line_total_cents: number;
};

export type Order = {
  id: UUID;
  order_number: string;
  status: OrderStatus;
  payment_status: PaymentStatus;
  currency: string;
  subtotal_cents: number;
  shipping_cents: number;
  tax_cents: number;
  total_cents: number;
  customer_name: string;
  customer_email: string;
  shipping: ShippingAddress;
  items: OrderItem[];
  confirmed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type OrderPage = {
  items: Order[];
  total: number;
  limit: number;
  offset: number;
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
