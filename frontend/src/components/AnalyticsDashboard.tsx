import { Users, Activity, Camera, Shield, AlertTriangle, Calendar, Gauge, CheckCircle } from "lucide-react";
import { MetricCard } from "./MetricCard";
import type { AnalyticsOverview } from "../types";

type Props = { data: AnalyticsOverview | null };

export function AnalyticsDashboard({ data }: Props) {
  if (!data) {
    return (
      <div className="rounded-[2rem] border border-white/10 bg-panel/70 px-6 py-12 text-center text-mist/50 shadow-panel">
        Loading analytics…
      </div>
    );
  }

  const unavailable = data.data_status !== "live" && data.data_status !== "partial";
  const display = (value: number | string | null, digits = 0) =>
    value === null || value === undefined
      ? "Unavailable"
      : typeof value === "number" && digits > 0
        ? value.toFixed(digits)
        : typeof value === "number"
          ? value.toLocaleString()
          : value;

  const cards = [
    { title: "Total Students", value: display(data.total_students), subtitle: "Verified school-owned records", icon: Users, color: "blue" as const },
    { title: "Attendance Rate", value: display(data.attendance_rate, 1), unit: data.attendance_rate == null ? undefined : "%", subtitle: "Verified attendance feed", icon: Calendar, color: "green" as const },
    { title: "Active Cameras", value: display(data.active_cameras), subtitle: "Recent camera health telemetry", icon: Camera, color: "blue" as const },
    { title: "System Uptime", value: display(data.uptime_percent, 1), unit: data.uptime_percent == null ? undefined : "%", subtitle: "Measured service availability", icon: Activity, color: "green" as const },
    { title: "Incidents Today", value: display(data.incidents_today), subtitle: "Persisted, reviewed incident events", icon: AlertTriangle, color: "orange" as const },
    { title: "Weekly Incidents", value: display(data.incidents_week), subtitle: "Verified rolling 7-day total", icon: Shield, color: "orange" as const },
    { title: "Avg Crowd Density", value: display(data.avg_crowd_density, 2), subtitle: "Validated density observations", icon: Gauge, color: "blue" as const },
    { title: "Compliance Score", value: display(data.compliance_score, 1), unit: data.compliance_score == null ? undefined : "%", subtitle: "Audited governance evidence", icon: CheckCircle, color: "green" as const },
  ];

  return (
    <div className="space-y-4">
      {unavailable && (
        <div role="status" aria-live="polite" className="rounded-xl border border-warning/40 bg-warning/10 px-4 py-3 text-sm text-warning">
          <strong className="block">LIVE ANALYTICS UNAVAILABLE</strong>
          <span>{data.data_notice}</span>
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <MetricCard key={card.title} {...card} />
        ))}
      </div>
      <section className="rounded-[2rem] border border-white/10 bg-panel/90 p-6 shadow-panel backdrop-blur">
        <p className="text-xs uppercase tracking-[0.28em] text-mist/50">Data integrity</p>
        <h3 className="mt-2 text-xl font-semibold text-white">Operational metrics require verified sources</h3>
        <p className="mt-3 text-sm text-mist/65">
          Metrics will appear when a tenant-scoped source is connected and its provenance and freshness can be verified.
          Seeded demonstration records are not treated as live school evidence.
        </p>
        <p className="mt-3 text-xs text-mist/45">Response generated: {new Date(data.generated_at).toLocaleString()}</p>
      </section>
    </div>
  );
}
