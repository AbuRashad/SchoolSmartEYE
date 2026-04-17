import type { LucideIcon } from "lucide-react";

type MetricCardProps = {
  title: string;
  value: string | number;
  unit?: string;
  subtitle?: string;
  trend?: "up" | "down" | "stable";
  trendValue?: string;
  icon: LucideIcon;
  color?: "green" | "red" | "blue" | "orange" | "purple";
};

const colorMap = {
  green: { text: "#46c37b", bg: "bg-safe/10", border: "border-safe/20" },
  red: { text: "#e84d5b", bg: "bg-critical/10", border: "border-critical/20" },
  blue: { text: "#4f8fd8", bg: "bg-sky/10", border: "border-sky/20" },
  orange: { text: "#ffb84d", bg: "bg-warning/10", border: "border-warning/20" },
  purple: { text: "#9b6dff", bg: "bg-[#9b6dff]/10", border: "border-[#9b6dff]/20" },
};

const trendArrow = { up: "▲", down: "▼", stable: "→" };
const trendColor = { up: "#46c37b", down: "#e84d5b", stable: "#ffb84d" };

export function MetricCard({ title, value, unit, subtitle, trend, trendValue, icon: Icon, color = "blue" }: MetricCardProps) {
  const c = colorMap[color];

  return (
    <div className={`rounded-[1.6rem] border ${c.border} bg-panel/90 p-5 shadow-panel backdrop-blur`}>
      <div className="flex items-start justify-between gap-3">
        <div className={`rounded-[1rem] ${c.bg} p-2.5`}>
          <Icon className="h-5 w-5" style={{ color: c.text }} />
        </div>
        {trend && trendValue && (
          <span className="text-[11px] font-semibold" style={{ color: trendColor[trend] }}>
            {trendArrow[trend]} {trendValue}
          </span>
        )}
      </div>
      <div className="mt-3">
        <p className="text-[10px] uppercase tracking-[0.26em] text-mist/50">{title}</p>
        <div className="mt-1.5 flex items-end gap-1.5">
          <span className="text-3xl font-bold text-white leading-none">{value}</span>
          {unit && <span className="mb-0.5 text-sm text-mist/50">{unit}</span>}
        </div>
        {subtitle && <p className="mt-1.5 text-xs text-mist/55">{subtitle}</p>}
      </div>
    </div>
  );
}
