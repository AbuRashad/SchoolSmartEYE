type KpiGaugeProps = {
  value: number;
  benchmark: number;
};

export function KpiGauge({ value, benchmark }: KpiGaugeProps) {
  const normalized = Math.max(0, Math.min(100, value));
  const circumference = 2 * Math.PI * 70;
  const progress = circumference - (normalized / 100) * circumference;
  const isBelow = normalized < benchmark;
  const tone = normalized >= benchmark ? "#46c37b" : normalized >= benchmark - 10 ? "#ffb84d" : "#e84d5b";
  const pulseR = 82;
  const pulseCirc = 2 * Math.PI * pulseR;

  return (
    <section className="rounded-[2rem] border border-white/10 bg-panel/90 p-6 shadow-panel backdrop-blur">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-mist/55">School Safety Index</p>
          <h2 className="mt-3 text-4xl font-semibold text-white">{normalized.toFixed(0)}</h2>
          <p className="mt-2 text-sm text-mist/75">Live institutional safety benchmarked against national threshold {benchmark}.</p>
          <p className="mt-2 text-xs font-semibold" style={{ color: tone }}>
            {normalized >= benchmark ? "▲" : "▼"} {isBelow ? `${(benchmark - normalized).toFixed(1)} pts below benchmark` : `+${(normalized - benchmark).toFixed(1)} pts above benchmark`}
          </p>
          <p className="mt-1 text-xs text-mist/40">▲ +2.3 pts from yesterday</p>
        </div>
        <div className="relative">
          <svg viewBox="0 0 180 180" className="h-40 w-40">
            {/* Pulse ring when below benchmark */}
            {isBelow && (
              <circle
                cx="90"
                cy="90"
                r={pulseR}
                fill="none"
                stroke="#e84d5b"
                strokeWidth="2"
                strokeDasharray={pulseCirc}
                strokeDashoffset={pulseCirc * 0.15}
                transform="rotate(-90 90 90)"
                opacity="0.5"
              >
                <animate attributeName="opacity" values="0.5;0.1;0.5" dur="1.6s" repeatCount="indefinite" />
                <animate attributeName="r" values={`${pulseR};${pulseR + 4};${pulseR}`} dur="1.6s" repeatCount="indefinite" />
              </circle>
            )}
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
      </div>

      {/* Color zones legend */}
      <div className="mt-4 flex gap-2 border-t border-white/10 pt-4">
        <div className="flex flex-1 items-center gap-1.5 rounded-[1rem] border border-critical/20 bg-critical/8 px-3 py-2">
          <span className="h-2 w-2 rounded-full bg-critical" />
          <span className="text-[10px] text-mist/60">{"Low < 65"}</span>
        </div>
        <div className="flex flex-1 items-center gap-1.5 rounded-[1rem] border border-warning/20 bg-warning/8 px-3 py-2">
          <span className="h-2 w-2 rounded-full bg-warning" />
          <span className="text-[10px] text-mist/60">Approaching 65–75</span>
        </div>
        <div className="flex flex-1 items-center gap-1.5 rounded-[1rem] border border-safe/20 bg-safe/8 px-3 py-2">
          <span className="h-2 w-2 rounded-full bg-safe" />
          <span className="text-[10px] text-mist/60">Healthy &gt; 75</span>
        </div>
      </div>
    </section>
  );
}