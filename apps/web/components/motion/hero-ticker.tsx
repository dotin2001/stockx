export function HeroTicker() {
  const phrase = "Change your life but keep your style";
  return (
    <div className="overflow-hidden border-y border-ink-200 bg-white py-3" aria-label={phrase}>
      <div className="ticker-track flex w-[200%] gap-10 whitespace-nowrap text-sm font-bold uppercase tracking-[0.25em] text-ink-700" aria-hidden="true">
        {Array.from({ length: 8 }).map((_, index) => (
          <span key={index}>{phrase}</span>
        ))}
      </div>
    </div>
  );
}
