"use client";

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
  if (!value.trim()) {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0
    ? Math.round(parsed * 100)
    : null;
}

export function DiscoveryControls({
  metadata,
}: {
  metadata: ProductDiscoveryMetadata;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const selected: ProductDiscoveryQueryParams = {
    brand: metadata.selected.brands,
    size: metadata.selected.sizes,
    min_price: metadata.selected.min_price_cents,
    max_price: metadata.selected.max_price_cents,
    available_only: metadata.selected.available_only,
    sort: metadata.sort,
  };
  const hasFilters = hasActiveDiscoveryFilters(selected);

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

  return (
    <aside className="surface grid gap-5 p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-black uppercase tracking-wide">
            Filters
          </h2>
          <p className="mt-1 text-xs font-semibold text-ink-500">
            {formatCount(metadata.total)} results
          </p>
        </div>
        {hasFilters ? (
          <button
            type="button"
            onClick={clearFilters}
            className="text-xs font-bold text-market-green hover:text-ink-900"
          >
            Clear
          </button>
        ) : null}
      </div>

      {hasFilters ? (
        <div className="flex flex-wrap gap-2" aria-label="Active filters">
          {metadata.selected.brands.map((brand) => (
            <FilterChip
              key={`brand-${brand}`}
              label={brand}
              onRemove={() =>
                update({ brand: toggleValue(selected.brand, brand) })
              }
            />
          ))}
          {metadata.selected.sizes.map((size) => (
            <FilterChip
              key={`size-${size}`}
              label={`Size ${size}`}
              onRemove={() =>
                update({ size: toggleValue(selected.size, size) })
              }
            />
          ))}
          {metadata.selected.min_price_cents !== null ? (
            <FilterChip
              label={`Min ${formatMoney(metadata.selected.min_price_cents)}`}
              onRemove={() => update({ min_price: null })}
            />
          ) : null}
          {metadata.selected.max_price_cents !== null ? (
            <FilterChip
              label={`Max ${formatMoney(metadata.selected.max_price_cents)}`}
              onRemove={() => update({ max_price: null })}
            />
          ) : null}
          {metadata.selected.available_only ? (
            <FilterChip
              label="Available only"
              onRemove={() => update({ available_only: false })}
            />
          ) : null}
        </div>
      ) : null}

      <label className="grid gap-2 text-sm font-bold text-ink-700">
        Sort
        <select
          value={metadata.sort}
          onChange={(event) =>
            update({ sort: event.target.value as ProductDiscoverySort })
          }
          className="border border-ink-200 bg-white px-3 py-2 text-sm font-semibold text-ink-900"
        >
          {Object.entries(SORT_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>

      <fieldset className="grid gap-3">
        <legend className="text-sm font-black uppercase tracking-wide">
          Availability
        </legend>
        <label className="flex items-center gap-3 text-sm font-semibold text-ink-700">
          <input
            type="checkbox"
            checked={metadata.selected.available_only}
            onChange={(event) =>
              update({ available_only: event.target.checked })
            }
            className="h-4 w-4 accent-market-green"
          />
          Available only
        </label>
      </fieldset>

      <fieldset className="grid gap-3">
        <legend className="text-sm font-black uppercase tracking-wide">
          Price
        </legend>
        <div className="grid grid-cols-2 gap-3">
          <label className="grid gap-1 text-xs font-bold text-ink-600">
            Min $
            <input
              type="number"
              min="0"
              inputMode="numeric"
              value={dollarsFromCents(metadata.selected.min_price_cents)}
              placeholder={dollarsFromCents(metadata.price_bounds.min_cents)}
              onChange={(event) =>
                update({ min_price: centsFromDollars(event.target.value) })
              }
              className="border border-ink-200 px-3 py-2 text-sm font-semibold text-ink-900 w-full "
            />
          </label>
          <label className="grid gap-1 text-xs font-bold text-ink-600">
            Max $
            <input
              type="number"
              min="0"
              inputMode="numeric"
              value={dollarsFromCents(metadata.selected.max_price_cents)}
              placeholder={dollarsFromCents(metadata.price_bounds.max_cents)}
              onChange={(event) =>
                update({ max_price: centsFromDollars(event.target.value) })
              }
              className="border border-ink-200 px-3 py-2 text-sm font-semibold text-ink-900 w-full"
            />
          </label>
        </div>
      </fieldset>

      <FacetGroup
        title="Brand"
        values={metadata.selected.brands}
        options={metadata.brands}
        onToggle={(value) =>
          update({ brand: toggleValue(selected.brand, value) })
        }
      />
      <FacetGroup
        title="Size"
        values={metadata.selected.sizes}
        options={metadata.sizes}
        onToggle={(value) =>
          update({ size: toggleValue(selected.size, value) })
        }
      />
    </aside>
  );
}

function FacetGroup({
  title,
  values,
  options,
  onToggle,
}: {
  title: string;
  values: string[];
  options: ProductDiscoveryMetadata["brands"];
  onToggle: (value: string) => void;
}) {
  return (
    <fieldset className="grid gap-3">
      <legend className="text-sm font-black uppercase tracking-wide">
        {title}
      </legend>
      {options.length === 0 ? (
        <p className="text-xs font-semibold text-ink-500">No options</p>
      ) : null}
      <div className="grid max-h-52 gap-2 overflow-auto pr-1">
        {options.map((option) => (
          <label
            key={option.value}
            className="flex items-center justify-between gap-3 text-sm font-semibold text-ink-700"
          >
            <span className="flex min-w-0 items-center gap-3">
              <input
                type="checkbox"
                checked={values.includes(option.value)}
                onChange={() => onToggle(option.value)}
                className="h-4 w-4 shrink-0 accent-market-green"
              />
              <span className="truncate">{option.label}</span>
            </span>
            <span className="shrink-0 text-xs text-ink-500">
              {formatCount(option.count)}
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

function FilterChip({
  label,
  onRemove,
}: {
  label: string;
  onRemove: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onRemove}
      className="inline-flex max-w-full items-center gap-2 border border-ink-200 bg-ink-50 px-2.5 py-1 text-xs font-bold text-ink-700 hover:border-market-green hover:text-market-green"
    >
      <span className="truncate">{label}</span>
      <span aria-hidden="true">x</span>
      <span className="sr-only">Remove {label}</span>
    </button>
  );
}
