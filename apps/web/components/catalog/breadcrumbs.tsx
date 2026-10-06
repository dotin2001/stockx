import Link from "next/link";

export function Breadcrumbs({ items }: { items: { label: string; href?: string }[] }) {
  return (
    <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-2 text-sm text-ink-500">
      <Link href="/" className="font-medium text-ink-700 hover:text-market-green">
        Home
      </Link>
      {items.map((item) => (
        <span key={item.label} className="flex items-center gap-2">
          <span>/</span>
          {item.href ? (
            <Link href={item.href} className="font-medium text-ink-700 hover:text-market-green">
              {item.label}
            </Link>
          ) : (
            <span>{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
