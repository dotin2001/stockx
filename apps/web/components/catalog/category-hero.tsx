import type { CategoryMeta } from "@/lib/category-meta";

export function CategoryHero({ meta }: { meta: CategoryMeta }) {
  return (
    <section className="relative overflow-hidden bg-ink-900 text-white">
      <div className="absolute inset-0 opacity-55">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={meta.imageUrl} alt="" className="h-full w-full object-cover" />
      </div>
      <div className="relative page-shell flex min-h-72 items-center py-12">
        <div className="max-w-2xl">
          <p className="text-sm font-bold uppercase tracking-[0.25em] text-white/80">Browse</p>
          <h1 className="mt-3 text-5xl font-black uppercase tracking-normal sm:text-6xl">{meta.label}</h1>
          <p className="mt-4 max-w-xl text-base leading-7 text-white/90">{meta.description}</p>
        </div>
      </div>
    </section>
  );
}
