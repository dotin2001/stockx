"use client";

import { FormEvent, useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type {
  ProductDiscoveryMetadata,
  ProductDiscoveryQueryParams,
  ProductDiscoverySort,
} from "@/lib/types";
import {
  clearDiscoveryHref,
  hasActiveDiscoveryFilters,
  nextDiscoveryHref,
  toggleValue,
} from "@/lib/discovery-params";
import { formatCount, formatMoney } from "@/lib/format";

const SORT_LABELS: Record<ProductDiscoverySort, string> = {
  newest: "Newest",
  price_asc: "Price: Low to High",
  price_desc: "Price: High to Low",
  popular: "Most Popular",
  name_asc: "Name: A to Z",
};

function dollarsFromCents(cents: number | null) {
  return cents === null ? "" : String(Math.round(cents / 100));
}

function centsFromDollars(value: string) {
  if (!value.trim()) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0
    ? Math.round(parsed * 100)
    : null;
}

export function DiscoveryControls({ metadata }: { metadata: ProductDiscoveryMetadata }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [minPrice, setMinPrice] = useState(dollarsFromCents(metadata.selected.min_price_cents));
  const [maxPrice, setMaxPrice] = useState(dollarsFromCents(metadata.selected.max_price_cents));
  const selected: ProductDiscoveryQueryParams = {
    brand: metadata.selected.brands,
    size: metadata.selected.sizes,
    min_price: metadata.selected.min_price_cents,
    max_price: metadata.selected.max_price_cents,
    available_only: metadata.selected.available_only,
    sort: metadata.sort,
  };
  const hasFilters = hasActiveDiscoveryFilters(selected);
  const activeFilterCount =
    metadata.selected.brands.length +
    metadata.selected.sizes.length +
    Number(metadata.selected.min_price_cents !== null) +
    Number(metadata.selected.max_price_cents !== null) +
    Number(metadata.selected.available_only);

  useEffect(() => {
    setMinPrice(dollarsFromCents(metadata.selected.min_price_cents));
    setMaxPrice(dollarsFromCents(metadata.selected.max_price_cents));
  }, [metadata.selected.max_price_cents, metadata.selected.min_price_cents]);

  function update(updates: ProductDiscoveryQueryParams) {
    router.push(
      nextDiscoveryHref(pathname, searchParams, {
        ...updates,
        sort: updates.sort ?? metadata.sort,
      }),
    );
  }

  function clearFilters() {
    router.push(clearDiscoveryHref(pathname, searchParams));
  }

  function applyPrice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    update({
      min_price: centsFromDollars(minPrice),
      max_price: centsFromDollars(maxPrice),
    });
  }

  return (
    <aside className="self-start lg:sticky lg:top-24">
      <div className="surface overflow-hidden border-ink-200 shadow-sm lg:max-h-[calc(100vh-7rem)] lg:overflow-y-auto">
        <button
          type="button"
          aria-expanded={isMobileOpen}
          aria-controls="catalog-filter-panel"
          onClick={() => setIsMobileOpen((isOpen) => !isOpen)}
          className="flex min-h-14 w-full items-center justify-between gap-4 px-4 text-left transition-colors hover:bg-ink-50 lg:hidden"
        >
          <span className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-full bg-market-mint text-market-green">
              <FilterIcon />
            </span>
            <span>
              <span className="block text-sm font-black text-ink-900">Filter &amp; sort</span>
              <span className="block text-xs font-semibold text-ink-500">
                {formatCount(metadata.total)} results
              </span>
            </span>
          </span>
          <span className="flex items-center gap-2">
            {activeFilterCount > 0 ? (
              <span className="grid min-w-6 place-items-center rounded-full bg-market-green px-1.5 py-0.5 text-xs font-black text-white">
                {activeFilterCount}
              </span>
            ) : null}
            <ChevronIcon className={`transition-transform duration-200 ${isMobileOpen ? "rotate-180" : ""}`} />
          </span>
        </button>

        <div id="catalog-filter-panel" className={`${isMobileOpen ? "block" : "hidden"} lg:block`}>
          <div className="hidden items-center justify-between gap-4 border-b border-ink-100 px-5 py-5 lg:flex">
            <div className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-full bg-market-mint text-market-green">
                <FilterIcon />
              </span>
              <div>
                <h2 className="text-base font-black text-ink-900">Filters</h2>
                <p className="text-xs font-semibold text-ink-500" aria-live="polite">
                  {formatCount(metadata.total)} results
                </p>
              </div>
            </div>
            {activeFilterCount > 0 ? (
              <span className="grid min-w-7 place-items-center rounded-full bg-market-green px-2 py-1 text-xs font-black text-white">
                {activeFilterCount}
              </span>
            ) : null}
          </div>

          <div className="grid gap-0">
            {hasFilters ? (
              <div className="border-b border-ink-100 bg-ink-50/70 px-4 py-4 lg:px-5">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <p className="text-xs font-black uppercase tracking-[0.12em] text-ink-500">Applied filters</p>
                  <button type="button" onClick={clearFilters} className="min-h-9 px-1 text-xs font-black text-market-green transition-colors hover:text-ink-900">
                    Clear all
                  </button>
                </div>
                <div className="flex flex-wrap gap-2" aria-label="Active filters">
                  {metadata.selected.brands.map((brand) => (
                    <FilterChip key={`brand-${brand}`} label={brand} onRemove={() => update({ brand: toggleValue(selected.brand, brand) })} />
                  ))}
                  {metadata.selected.sizes.map((size) => (
                    <FilterChip key={`size-${size}`} label={`Size ${size}`} onRemove={() => update({ size: toggleValue(selected.size, size) })} />
                  ))}
                  {metadata.selected.min_price_cents !== null ? (
                    <FilterChip label={`From ${formatMoney(metadata.selected.min_price_cents)}`} onRemove={() => update({ min_price: null })} />
                  ) : null}
                  {metadata.selected.max_price_cents !== null ? (
                    <FilterChip label={`Up to ${formatMoney(metadata.selected.max_price_cents)}`} onRemove={() => update({ max_price: null })} />
                  ) : null}
                  {metadata.selected.available_only ? (
                    <FilterChip label="Available" onRemove={() => update({ available_only: false })} />
                  ) : null}
                </div>
              </div>
            ) : null}

            <div className="border-b border-ink-100 px-4 py-5 lg:px-5">
              <label className="grid gap-2 text-sm font-black text-ink-900">
                Sort by
                <span className="relative">
                  <select
                    value={metadata.sort}
                    onChange={(event) => update({ sort: event.target.value as ProductDiscoverySort })}
                    className="min-h-11 w-full appearance-none rounded-lg border border-ink-200 bg-white px-3.5 pr-10 text-sm font-semibold text-ink-900 transition-colors hover:border-ink-500 focus:border-market-green"
                  >
                    {Object.entries(SORT_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                  <ChevronIcon className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink-500" />
                </span>
              </label>
            </div>

            <fieldset className="border-b border-ink-100 px-4 py-5 lg:px-5">
              <legend className="sr-only">Availability</legend>
              <label className="flex cursor-pointer items-center justify-between gap-4 py-1 text-sm">
                <span>
                  <span className="block font-black text-ink-900">Available now</span>
                  <span className="mt-0.5 block text-xs font-semibold text-ink-500">Hide products without listings</span>
                </span>
                <input
                  type="checkbox"
                  checked={metadata.selected.available_only}
                  onChange={(event) => update({ available_only: event.target.checked })}
                  className="peer sr-only"
                />
                <span className="relative h-6 w-11 shrink-0 rounded-full bg-ink-200 transition-colors after:absolute after:left-0.5 after:top-0.5 after:h-5 after:w-5 after:rounded-full after:bg-white after:shadow-sm after:transition-transform peer-checked:bg-market-green peer-checked:after:translate-x-5 peer-focus-visible:ring-2 peer-focus-visible:ring-market-green peer-focus-visible:ring-offset-2" />
              </label>
            </fieldset>

            <form onSubmit={applyPrice} className="border-b border-ink-100 px-4 py-5 lg:px-5">
              <fieldset>
                <legend className="text-sm font-black text-ink-900">Price range</legend>
                <div className="mt-3 grid grid-cols-[1fr_auto_1fr] items-end gap-2">
                  <PriceInput label="Minimum" value={minPrice} placeholder={dollarsFromCents(metadata.price_bounds.min_cents)} onChange={setMinPrice} />
                  <span className="pb-3 text-xs font-bold text-ink-300" aria-hidden="true">—</span>
                  <PriceInput label="Maximum" value={maxPrice} placeholder={dollarsFromCents(metadata.price_bounds.max_cents)} onChange={setMaxPrice} />
                </div>
                <button type="submit" className="mt-3 min-h-10 w-full rounded-lg border border-ink-900 bg-ink-900 px-4 text-xs font-black text-white transition-colors hover:border-market-green hover:bg-market-green">
                  Apply price
                </button>
              </fieldset>
            </form>

            <FacetGroup title="Brand" values={metadata.selected.brands} options={metadata.brands} onToggle={(value) => update({ brand: toggleValue(selected.brand, value) })} />
            <FacetGroup title="Size" values={metadata.selected.sizes} options={metadata.sizes} onToggle={(value) => update({ size: toggleValue(selected.size, value) })} isLast />
          </div>
        </div>
      </div>
    </aside>
  );
}

function PriceInput({ label, value, placeholder, onChange }: { label: string; value: string; placeholder: string; onChange: (value: string) => void }) {
  return (
    <label className="grid min-w-0 gap-1.5 text-xs font-bold text-ink-500">
      {label}
      <span className="relative">
        <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm font-bold text-ink-500">$</span>
        <input
          type="number"
          min="0"
          inputMode="numeric"
          value={value}
          placeholder={placeholder}
          onChange={(event) => onChange(event.target.value)}
          className="min-h-11 w-full rounded-lg border border-ink-200 bg-white py-2 pl-7 pr-2 text-sm font-bold text-ink-900 transition-colors placeholder:text-ink-300 hover:border-ink-500 focus:border-market-green"
        />
      </span>
    </label>
  );
}

function FacetGroup({ title, values, options, onToggle, isLast = false }: { title: string; values: string[]; options: ProductDiscoveryMetadata["brands"]; onToggle: (value: string) => void; isLast?: boolean }) {
  return (
    <fieldset className={`px-4 py-5 lg:px-5 ${isLast ? "" : "border-b border-ink-100"}`}>
      <legend className="mb-3 w-full text-sm font-black text-ink-900">
        <span className="flex items-center justify-between gap-3">
          {title}
          {values.length > 0 ? (
            <span className="rounded-full bg-market-mint px-2 py-0.5 text-xs font-black text-market-green">{values.length}</span>
          ) : null}
        </span>
      </legend>
      {options.length === 0 ? (
        <p className="rounded-lg bg-ink-50 px-3 py-2.5 text-xs font-semibold text-ink-500">No options available</p>
      ) : null}
      <div className="grid max-h-56 gap-1 overflow-y-auto pr-1">
        {options.map((option) => (
          <label key={option.value} className="flex min-h-10 cursor-pointer items-center justify-between gap-3 rounded-lg border border-transparent px-2 py-1.5 text-sm font-semibold text-ink-700 transition-colors hover:bg-ink-50 has-[:checked]:border-market-green/20 has-[:checked]:bg-market-mint has-[:checked]:text-ink-900">
            <span className="flex min-w-0 items-center gap-3">
              <input type="checkbox" checked={values.includes(option.value)} onChange={() => onToggle(option.value)} className="peer sr-only" />
              <span className="grid h-5 w-5 shrink-0 place-items-center rounded border border-ink-300 bg-white text-white transition-colors peer-checked:border-market-green peer-checked:bg-market-green peer-focus-visible:ring-2 peer-focus-visible:ring-market-green peer-focus-visible:ring-offset-2">
                <CheckIcon />
              </span>
              <span className="truncate">{option.label}</span>
            </span>
            <span className="shrink-0 rounded-full bg-white px-2 py-0.5 text-[11px] font-bold text-ink-500 ring-1 ring-inset ring-ink-100">{formatCount(option.count)}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function FilterChip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <button type="button" onClick={onRemove} className="inline-flex min-h-8 max-w-full items-center gap-1.5 rounded-full border border-market-green/20 bg-white px-3 py-1 text-xs font-bold text-ink-700 shadow-sm transition-colors hover:border-market-green hover:text-market-green">
      <span className="truncate">{label}</span>
      <CloseIcon />
      <span className="sr-only">Remove {label}</span>
    </button>
  );
}

function FilterIcon() {
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-5 w-5"><path d="M4 6h16M7 12h10M10 18h4" strokeLinecap="round" /></svg>;
}

function ChevronIcon({ className = "" }: { className?: string }) {
  return <svg aria-hidden="true" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="2" className={`h-4 w-4 ${className}`}><path d="m5 7.5 5 5 5-5" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

function CheckIcon() {
  return <svg aria-hidden="true" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" className="h-3 w-3"><path d="m3 8 3 3 7-7" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

function CloseIcon() {
  return <svg aria-hidden="true" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" className="h-3.5 w-3.5"><path d="m4 4 8 8m0-8-8 8" strokeLinecap="round" /></svg>;
}
