import type { ReactNode } from "react";

export function AuthFlowShell({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children: ReactNode }) {
  return (
    <section className="surface mx-auto grid w-full max-w-lg gap-6 p-5 sm:p-8" aria-labelledby="auth-flow-title">
      <div>
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-market-green">{eyebrow}</p>
        <h1 id="auth-flow-title" className="mt-2 text-3xl font-black text-ink-900">{title}</h1>
        <p className="mt-3 text-sm leading-6 text-ink-500">{description}</p>
      </div>
      {children}
    </section>
  );
}
