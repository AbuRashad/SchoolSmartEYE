import { useMemo } from "react";
import type { SSIHistoryPoint } from "../types";

type SSIHistoryChartProps = {
  scores: SSIHistoryPoint[];
  benchmark: number;
  average: number;
  trend: string;
};

const W = 700;
const H = 220;
const PAD = { top: 20, right: 24, bottom: 36, left: 48 };
const PLOT_W = W - PAD.left - PAD.right;
const PLOT_H = H - PAD.top - PAD.bottom;

function trendIcon(trend: string) {
  if (trend === "improving") return "↗";
  if (trend === "declining") return "↘";
  return "→";
}

function trendColor(trend: string) {
  if (trend === "improving") return "#46c37b";
  if (trend === "declining") return "#e84d5b";
  return "#ffb84d";
}

export function SSIHistoryChart({ scores, benchmark, average, trend }: SSIHistoryChartProps) {
  const { polyline, dots, benchmarkY } = useMemo(() => {
    const minSSI = 40;
    const maxSSI = 100;
    const toX = (i: number) => PAD.left + (i / (scores.length - 1)) * PLOT_W;
    const toY = (v: number) => PAD.top + PLOT_H - ((v - minSSI) / (maxSSI - minSSI)) * PLOT_H;

    const pts = scores.map((s, i) => ({ x: toX(i), y: toY(s.ssi), ssi: s.ssi, day: s.day }));
    const polyline = pts.map((p) => `${p.x},${p.y}`).join(" ");
    const bY = toY(benchmark);

    return { polyline, dots: pts, benchmarkY: bY };
  }, [scores, benchmark]);

  const tc = trendColor(trend);

  return (
    <section className="rounded-[2rem] border border-white/10 bg-panel/90 p-6 shadow-panel backdrop-blur">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-mist/55">30-Day Trend</p>
          <h2 className="mt-2 text-xl font-semibold text-white">School Safety Index History</h2>
        </div>
        <div className="flex items-center gap-4">
          <div className="rounded-[1.2rem] border border-white/10 bg-white/5 px-4 py-2 text-center">
            <p className="text-[10px] uppercase tracking-[0.22em] text-mist/50">Average SSI</p>
            <p className="mt-1 text-2xl font-semibold text-white">{average.toFixed(1)}</p>
          </div>
          <div className="rounded-[1.2rem] border border-white/10 bg-white/5 px-4 py-2 text-center">
            <p className="text-[10px] uppercase tracking-[0.22em] text-mist/50">Trend</p>
            <p className="mt-1 text-2xl font-semibold" style={{ color: tc }}>
              {trendIcon(trend)} {trend}
            </p>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[400px]">
          {/* Grid lines */}
          {[40, 55, 70, 85, 100].map((v) => {
            const y = PAD.top + PLOT_H - ((v - 40) / 60) * PLOT_H;
            return (
              <g key={v}>
                <line x1={PAD.left} y1={y} x2={W - PAD.right} y2={y} stroke="#1f3a5c" strokeWidth="1" strokeDasharray="4 4" />
                <text x={PAD.left - 8} y={y + 4} textAnchor="end" className="fill-[#4a7ab5] text-[10px]">{v}</text>
              </g>
            );
          })}

          {/* Benchmark line */}
          <line x1={PAD.left} y1={benchmarkY} x2={W - PAD.right} y2={benchmarkY} stroke="#ffb84d" strokeWidth="1.5" strokeDasharray="6 3" />
          <text x={W - PAD.right + 4} y={benchmarkY + 4} className="fill-[#ffb84d] text-[10px]">BM {benchmark}</text>

          {/* Gradient fill */}
          <defs>
            <linearGradient id="ssiGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4f8fd8" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#4f8fd8" stopOpacity="0.02" />
            </linearGradient>
          </defs>
          <polygon
            points={`${PAD.left},${PAD.top + PLOT_H} ${polyline} ${W - PAD.right},${PAD.top + PLOT_H}`}
            fill="url(#ssiGrad)"
          />

          {/* Line */}
          <polyline points={polyline} fill="none" stroke="#4f8fd8" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />

          {/* Dots — only every 5th for clarity */}
          {dots.filter((_, i) => i % 5 === 0 || i === dots.length - 1).map((d) => (
            <g key={d.day}>
              <circle cx={d.x} cy={d.y} r="4" fill="#4f8fd8" stroke="#0d1b31" strokeWidth="2" />
              <text x={d.x} y={PAD.top + PLOT_H + 16} textAnchor="middle" className="fill-[#4a7ab5] text-[9px]">D{d.day}</text>
            </g>
          ))}
        </svg>
      </div>

      <div className="mt-4 flex items-center gap-6 text-xs text-mist/55">
        <span className="flex items-center gap-2"><span className="h-0.5 w-6 bg-sky inline-block" /> SSI Score</span>
        <span className="flex items-center gap-2"><span className="h-0.5 w-6 bg-warning inline-block" style={{ borderTop: "2px dashed #ffb84d" }} /> National Benchmark</span>
      </div>
    </section>
  );
}
