"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

export function SearchBar() {
  const router = useRouter();
  const [query, setQuery] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = query.trim();
    if (trimmed) {
      router.push(`/search?q=${encodeURIComponent(trimmed)}`);
    }
  }

  return (
    <form onSubmit={submit} role="search" className="relative flex min-w-0 flex-1">
      <label htmlFor="site-search" className="sr-only">
        Search products
      </label>
      <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-500" aria-hidden="true">
        <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="7" />
          <path d="m20 20-3.5-3.5" />
        </svg>
      </span>
      <input
        id="site-search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search for brands, color, etc"
        className="h-11 w-full border border-ink-200 bg-white pl-10 pr-4 text-sm text-ink-900 placeholder:text-ink-500"
      />
    </form>
  );
}
