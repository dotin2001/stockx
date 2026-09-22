export function formatMoney(cents: number | null, currency = "USD") {
  if (cents === null) {
    return "No asks yet";
  }

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0
  }).format(cents / 100);
}

export function formatCount(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

export function titleFromSlug(slug: string) {
  return slug
    .split("-")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
