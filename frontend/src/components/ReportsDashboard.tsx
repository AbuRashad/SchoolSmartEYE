import { Download } from "lucide-react";
import type { ReportItem, ReportStats } from "../types";

type Props = { reports: ReportItem[]; stats: ReportStats | null };

const typeColors: Record<ReportItem["type"], string> = {
  operational: "bg-sky/20 text-sky border-sky/30",
  analytical: "bg-[#9b6dff]/20 text-[#9b6dff] border-[#9b6dff]/30",
  supervisory: "bg-warning/20 text-warning border-warning/30",
  ministerial: "bg-safe/20 text-safe border-safe/30",
};

const statusColors: Record<ReportItem["status"], string> = {
  ready: "bg-safe/20 text-safe",
  generating: "bg-warning/20 text-warning",
  scheduled: "bg-white/10 text-mist/60",
};

export function ReportsDashboard({ reports, stats }: Props) {
  // SVG bar chart: Weekly Incidents by Day
  const weekData = stats?.weekly_incidents_by_day ?? [];
  const maxCount = Math.max(...weekData.map((d) => d.count), 1);
  const chartW = 340;
  const chartH = 120;
  const barW = 32;
  const gap = (chartW - weekData.length * barW) / (weekData.length + 1);

  // SVG horizontal bar chart: Top Risk Zones
  const zones = stats?.top_risk_zones ?? [];

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        {/* Left: Report list */}
        <section className="rounded-[2rem] border border-white/10 bg-panel/90 p-6 shadow-panel backdrop-blur">
          <p className="text-xs uppercase tracking-[0.28em] text-mist/50">Available Reports</p>
          <h3 className="mt-2 text-xl font-semibold text-white">Multi-Level Periodic Reports</h3>
          <div className="mt-5 space-y-3">
            {reports.map((r) => (
              <div
                key={r.id}
                className="flex items-center justify-between gap-4 rounded-[1.4rem] border border-white/10 bg-white/5 px-4 py-4"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.18em] ${typeColors[r.type]}`}>
                      {r.type}
                    </span>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${statusColors[r.status]}`}>
                      {r.status}
                    </span>
                  </div>
                  <p className="mt-2 text-sm font-semibold text-white truncate">{r.title}</p>
                  <p className="mt-0.5 text-xs text-mist/45">{r.period} · Generated {r.generated_at}</p>
                </div>
                {r.status === "ready" && (
                  <button
                    type="button"
                    className="flex shrink-0 items-center gap-1.5 rounded-[1rem] border border-sky/30 bg-sky/10 px-3 py-2 text-xs font-medium text-sky transition hover:bg-sky/20"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Export
                  </button>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* Right: Charts */}
        <div className="space-y-4">
          {/* Weekly incidents bar chart */}
          <section className="rounded-[2rem] border border-white/10 bg-panel/90 p-6 shadow-panel backdrop-blur">
            <p className="text-xs uppercase tracking-[0.28em] text-mist/50">Weekly Incidents by Day</p>
            <div className="mt-4 overflow-x-auto">
              <svg viewBox={`0 0 ${chartW} ${chartH + 28}`} width={chartW} height={chartH + 28}>
                {weekData.map((d, i) => {
                  const barH = (d.count / maxCount) * chartH;
                  const x = gap + i * (barW + gap);
                  const y = chartH - barH;
                  const fill = d.count >= 5 ? "#e84d5b" : d.count >= 3 ? "#ffb84d" : "#4f8fd8";
                  return (
                    <g key={d.day}>
                      <rect x={x} y={y} width={barW} height={barH} rx={6} fill={fill} opacity={0.85} />
                      <text x={x + barW / 2} y={chartH + 14} textAnchor="middle" fill="#93b6eb" fontSize="10">
                        {d.day}
                      </text>
                      {d.count > 0 && (
                        <text x={x + barW / 2} y={y - 4} textAnchor="middle" fill="white" fontSize="10" fontWeight="600">
                          {d.count}
                        </text>
                      )}
                    </g>
                  );
                })}
              </svg>
            </div>
          </section>

          {/* Top risk zones horizontal bars */}
          <section className="rounded-[2rem] border border-white/10 bg-panel/90 p-6 shadow-panel backdrop-blur">
            <p className="text-xs uppercase tracking-[0.28em] text-mist/50">Top Risk Zones</p>
            <div className="mt-4 space-y-3">
              {zones.map((z) => {
                const fill = z.risk >= 0.6 ? "#e84d5b" : z.risk >= 0.45 ? "#ffb84d" : "#46c37b";
                return (
                  <div key={z.zone}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-mist/70 truncate max-w-[160px]">{z.zone}</span>
                      <span className="text-xs font-bold text-white">{(z.risk * 100).toFixed(0)}%</span>
                    </div>
                    <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
                      <div
                        className="h-full rounded-full transition-all duration-700"
                        style={{ width: `${z.risk * 100}%`, backgroundColor: fill }}
                      />
                    </div>
                    <p className="mt-0.5 text-[10px] text-mist/40">{z.incidents} incidents</p>
                  </div>
                );
              })}
            </div>
          </section>
        </div>
      </div>

      {/* Bottom: Incident Type Breakdown */}
      {stats && (
        <section className="rounded-[2rem] border border-white/10 bg-panel/90 p-6 shadow-panel backdrop-blur">
          <p className="text-xs uppercase tracking-[0.28em] text-mist/50">Incident Type Breakdown</p>
          <div className="mt-5 grid gap-4 sm:grid-cols-2 md:grid-cols-4">
            {stats.incident_types.map((it) => {
              const total = stats.incident_types.reduce((s, x) => s + x.count, 0);
              const pct = total > 0 ? (it.count / total) * 100 : 0;
              return (
                <div key={it.type} className="rounded-[1.4rem] border border-white/10 bg-white/5 px-4 py-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-mist/60">{it.type}</span>
                    <span className="text-sm font-bold text-white">{it.count}</span>
                  </div>
                  <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${pct}%`, backgroundColor: it.color }}
                    />
                  </div>
                  <p className="mt-1.5 text-[10px] text-mist/40">{pct.toFixed(1)}% of total</p>
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
