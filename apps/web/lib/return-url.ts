const AUTH_ENTRY_PATHS = new Set([
  "/login",
  "/signup",
  "/forgot-password",
  "/reset-password",
  "/verify-email"
]);

function defaultOrigin() {
  return typeof window === "undefined" ? "http://localhost" : window.location.origin;
}

export function normalizeInternalReturnUrl(value: string | null | undefined, origin = defaultOrigin()): string | null {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return null;
  if (value.includes("\\") || /[\u0000-\u001f\u007f]/.test(value)) return null;

  try {
    const base = new URL(origin);
    const resolved = new URL(value, base);
    if (resolved.origin !== base.origin) return null;
    const pathname = resolved.pathname.replace(/\/$/, "") || "/";
    if (AUTH_ENTRY_PATHS.has(pathname)) return null;
    return `${resolved.pathname}${resolved.search}${resolved.hash}`;
  } catch {
    return null;
  }
}

export function safeInternalReturnUrl(value: string | null | undefined, fallback = "/account") {
  return normalizeInternalReturnUrl(value) ?? fallback;
}

export function currentProtectedReturnUrl() {
  if (typeof window === "undefined") return null;
  const path = `${window.location.pathname}${window.location.search}${window.location.hash}`;
  const protectedPrefixes = ["/account", "/admin", "/cart", "/checkout", "/orders", "/sell"];
  return protectedPrefixes.some((prefix) => window.location.pathname === prefix || window.location.pathname.startsWith(`${prefix}/`))
    ? normalizeInternalReturnUrl(path)
    : null;
}
