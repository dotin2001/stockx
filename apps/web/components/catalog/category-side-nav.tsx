import Link from "next/link";
import type { CategoryMeta } from "@/lib/category-meta";

export function CategorySideNav({ meta }: { meta: CategoryMeta }) {
  return (
    <aside className="surface p-5">
      <h2 className="text-sm font-black uppercase tracking-wide">{meta.label}</h2>
      <div className="mt-4 grid gap-2 text-sm font-semibold text-ink-600">
        {meta.filters.map((filter) => (
          <Link key={filter} href={`/search?q=${encodeURIComponent(filter)}`} className="py-1 hover:text-market-green">
            {filter}
          </Link>
        ))}
      </div>
    </aside>
  );
}
