"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/contexts/auth-context";
import { CategoryNav } from "@/components/layout/category-nav";
import { SearchBar } from "@/components/layout/search-bar";
import { StockXLogo } from "@/components/layout/stockx-logo";

const publicLinks = [
  { label: "Browse", href: "/category/sneakers" },
  { label: "News", href: "/" },
  { label: "About", href: "/" },
  { label: "Help", href: "/" }
];

export function SiteHeader() {
  const pathname = usePathname();
  const { status, user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [stuck, setStuck] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  useEffect(() => {
    const update = () => setStuck(window.scrollY > 4);
    update();
    window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, []);

  return (
    <header className={`sticky top-0 z-50 bg-white transition-shadow ${stuck ? "shadow-md" : "shadow-sm"}`}>
      <div className="page-shell flex min-h-20 items-center gap-4 py-4">
        <div className="flex shrink-0 items-center">
          <StockXLogo />
        </div>
        <div className="hidden min-w-0 flex-1 md:flex">
          <SearchBar />
        </div>
        <button
          type="button"
          className="ml-auto inline-flex h-11 w-11 items-center justify-center border border-ink-200 md:hidden"
          aria-label="Toggle navigation menu"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((open) => !open)}
        >
          <span className="sr-only">Menu</span>
          <svg viewBox="0 0 24 24" className={`h-5 w-5 motion-safe:transition-transform ${menuOpen ? "motion-safe:rotate-90" : ""}`} fill="none" stroke="currentColor" strokeWidth="2">
            {menuOpen ? <path d="M6 6l12 12M18 6 6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}
          </svg>
        </button>
        <nav className="hidden items-center gap-5 text-sm font-medium text-ink-700 md:flex" aria-label="Primary navigation">
          {publicLinks.map((link) => (
            <Link key={link.label} href={link.href} className="transition hover:text-market-green">
              {link.label}
            </Link>
          ))}
          {status === "authenticated" && user ? (
            <>
              {user.is_admin ? (
                <>
                  <Link href="/admin/products/new" className="transition hover:text-market-green">
                    Admin Products
                  </Link>
                  <Link href="/admin/messages" className="transition hover:text-market-green">
                    Messages
                  </Link>
                  {user.is_supreme_admin ? (
                    <Link href="/admin/users" className="transition hover:text-market-green">
                      Users
                    </Link>
                  ) : null}
                </>
              ) : null}
              <Link href="/account" className="transition hover:text-market-green">
                Account
              </Link>
              <button type="button" onClick={() => void logout()} className="transition hover:text-market-green">
                Logout
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="transition hover:text-market-green">
                Login
              </Link>
              <Link href="/signup" className="transition hover:text-market-green">
                Sign Up
              </Link>
            </>
          )}
          <Link href="/cart" className="border border-ink-300 px-4 py-2.5 font-semibold transition hover:border-market-green hover:text-market-green">
            Cart
          </Link>
        </nav>
      </div>
      <div className="page-shell pb-4 md:hidden">
        <SearchBar />
      </div>
      {menuOpen ? (
        <nav className="border-t border-ink-200 bg-white md:hidden" aria-label="Mobile navigation">
          <div className="page-shell grid gap-1 py-4 text-sm font-semibold text-ink-800">
            {[...publicLinks, { label: "Cart", href: "/cart" }].map((link) => (
              <Link key={link.label} href={link.href} className="px-2 py-3 transition hover:bg-ink-50 hover:text-market-green">
                {link.label}
              </Link>
            ))}
            {status === "authenticated" ? (
              <>
                {user?.is_admin ? (
                  <>
                    <Link href="/admin/products/new" className="px-2 py-3 transition hover:bg-ink-50 hover:text-market-green">
                      Admin Products
                    </Link>
                    <Link href="/admin/messages" className="px-2 py-3 transition hover:bg-ink-50 hover:text-market-green">
                      Messages
                    </Link>
                    {user?.is_supreme_admin ? (
                      <Link href="/admin/users" className="px-2 py-3 transition hover:bg-ink-50 hover:text-market-green">
                        Users
                      </Link>
                    ) : null}
                  </>
                ) : null}
                <Link href="/account" className="px-2 py-3 transition hover:bg-ink-50 hover:text-market-green">
                  Account
                </Link>
                <button type="button" onClick={() => void logout()} className="px-2 py-3 text-left transition hover:bg-ink-50 hover:text-market-green">
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link href="/login" className="px-2 py-3 transition hover:bg-ink-50 hover:text-market-green">
                  Login
                </Link>
                <Link href="/signup" className="px-2 py-3 transition hover:bg-ink-50 hover:text-market-green">
                  Sign Up
                </Link>
              </>
            )}
          </div>
        </nav>
      ) : null}
      <CategoryNav />
    </header>
  );
}
