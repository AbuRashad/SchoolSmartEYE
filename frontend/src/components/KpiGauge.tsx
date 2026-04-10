type KpiGaugeProps = {
  value: number;
  benchmark: number;
};

export function KpiGauge({ value, benchmark }: KpiGaugeProps) {
  const normalized = Math.max(0, Math.min(100, value));
  const circumference = 2 * Math.PI * 70;
  const progress = circumference - (normalized / 100) * circumference;
  const tone = normalized >= benchmark ? "#46c37b" : normalized >= benchmark - 10 ? "#ffb84d" : "#e84d5b";

  return (
    <section className="rounded-[2rem] border border-white/10 bg-panel/90 p-6 shadow-panel backdrop-blur">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-mist/55">School Safety Index</p>
          <h2 className="mt-3 text-4xl font-semibold text-white">{normalized.toFixed(0)}</h2>
          <p className="mt-2 text-sm text-mist/75">Live institutional safety benchmarked against national threshold {benchmark}.</p>
        </div>
        <svg viewBox="0 0 180 180" className="h-40 w-40">
          <circle cx="90" cy="90" r="70" fill="none" stroke="#18355b" strokeWidth="14" />
          <circle
            cx="90"
            cy="90"
            r="70"
            fill="none"
            stroke={tone}
            strokeWidth="14"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={progress}
            transform="rotate(-90 90 90)"
          />
          <text x="90" y="88" textAnchor="middle" className="fill-white text-[28px] font-semibold">
            {normalized.toFixed(0)}
          </text>
          <text x="90" y="108" textAnchor="middle" className="fill-[#93b6eb] text-[11px] uppercase tracking-[0.22em]">
            SSI
          </text>
        </svg>
      </div>
    </section>
  );
}