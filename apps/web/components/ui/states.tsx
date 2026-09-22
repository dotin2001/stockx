import Link from "next/link";

export function LoadingState({ label = "Loading marketplace data..." }: { label?: string }) {
  return (
    <div className="surface grid min-h-52 place-items-center px-6 py-10 text-center">
      <div>
        <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-ink-200 border-t-market-green" aria-hidden="true" />
        <p className="mt-4 text-sm font-semibold text-ink-600">{label}</p>
      </div>
    </div>
  );
}

export function ErrorState({ title = "Something went wrong", message, href = "/", action = "Return home" }: { title?: string; message?: string; href?: string; action?: string }) {
  return (
    <div className="surface px-6 py-10 text-center">
      <p className="text-sm font-semibold uppercase tracking-wide text-market-red">Error</p>
      <h2 className="mt-2 text-2xl font-bold">{title}</h2>
      <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-ink-500">{message ?? "The marketplace could not load this view."}</p>
      <Link href={href} className="mt-6 inline-flex bg-ink-900 px-5 py-3 text-sm font-bold text-white hover:bg-market-green">
        {action}
      </Link>
    </div>
  );
}

export function EmptyState({ title, message, href = "/", action = "Browse products" }: { title: string; message: string; href?: string; action?: string }) {
  return (
    <div className="surface px-6 py-10 text-center">
      <h2 className="text-2xl font-bold">{title}</h2>
      <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-ink-500">{message}</p>
      <Link href={href} className="mt-6 inline-flex border border-ink-900 px-5 py-3 text-sm font-bold text-ink-900 hover:bg-ink-900 hover:text-white">
        {action}
      </Link>
    </div>
  );
}
