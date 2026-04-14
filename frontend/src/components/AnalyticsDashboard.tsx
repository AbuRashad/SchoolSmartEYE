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

  const patrolWidth = `${data.patrol_efficiency}%`;
  const complianceWidth = `${data.compliance_score}%`;

  return (
    <div className="space-y-4">
      {/* Row 1 — 4 primary metrics */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Total Students"
          value={data.total_students.toLocaleString()}
          subtitle="Enrolled and tracked"
          icon={Users}
          color="blue"
          trend="stable"
          trendValue="No change"
        />
        <MetricCard
          title="Attendance Rate"
          value={data.attendance_rate.toFixed(1)}
          unit="%"
          subtitle="Today's attendance"
          icon={Calendar}
          color="green"
          trend="up"
          trendValue="+1.2% vs yesterday"
        />
        <MetricCard
          title="Active Cameras"
          value={data.active_cameras}
          subtitle={`of ${data.total_units * 2} total cameras`}
          icon={Camera}
          color="blue"
          trend="stable"
          trendValue="All nominal"
        />
        <MetricCard
          title="System Uptime"
          value={data.uptime_percent.toFixed(1)}
          unit="%"
          subtitle="Last 30 days"
          icon={Activity}
          color="green"
          trend="up"
          trendValue="SLA compliant"
        />
      </div>

      {/* Row 2 — 4 operational metrics */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Incidents Today"
          value={data.incidents_today}
          subtitle="Flagged by AI"
          icon={AlertTriangle}
          color={data.incidents_today > 5 ? "red" : data.incidents_today > 2 ? "orange" : "green"}
          trend={data.incidents_today > 3 ? "up" : "down"}
          trendValue={`${data.incidents_week} this week`}
        />
        <MetricCard
          title="Weekly Incidents"
          value={data.incidents_week}
          subtitle="7-day rolling total"
          icon={Shield}
          color="orange"
          trend="down"
          trendValue="-4 vs last week"
        />
        <MetricCard
          title="Avg Crowd Density"
          value={(data.avg_crowd_density * 100).toFixed(0)}
          unit="%"
          subtitle={`Peak: ${data.peak_density_zone}`}
          icon={Gauge}
          color={data.avg_crowd_density > 0.7 ? "red" : data.avg_crowd_density > 0.5 ? "orange" : "blue"}
          trend="stable"
          trendValue="Within threshold"
        />
        <MetricCard
          title="Compliance Score"
          value={data.compliance_score.toFixed(1)}
          unit="%"
          subtitle="Governance alignment"
          icon={CheckCircle}
          color="green"
          trend="up"
          trendValue="+0.3 pts"
        />
      </div>

      {/* Row 3 — System Intelligence Summary */}
      <section className="rounded-[2rem] border border-white/10 bg-panel/90 p-6 shadow-panel backdrop-blur">
        <p className="text-xs uppercase tracking-[0.28em] text-mist/50">System Intelligence Summary</p>
        <h3 className="mt-2 text-xl font-semibold text-white">Operational Performance Overview</h3>

        <div className="mt-6 grid gap-6 md:grid-cols-2">
          {/* Patrol Efficiency */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-mist/70">Patrol Efficiency</span>
              <span className="text-sm font-bold text-white">{data.patrol_efficiency.toFixed(1)}%</span>
            </div>
            <div className="h-2.5 w-full overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{ width: patrolWidth, background: "linear-gradient(90deg, #4f8fd8, #46c37b)" }}
              />
            </div>
            <p className="mt-1.5 text-xs text-mist/45">Average response time: 2.4 min · Coverage: 100%</p>
          </div>

          {/* Compliance Score bar */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-mist/70">Arab Governance Compliance</span>
              <span className="text-sm font-bold text-white">{data.compliance_score.toFixed(1)}%</span>
            </div>
            <div className="h-2.5 w-full overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{ width: complianceWidth, background: "linear-gradient(90deg, #9b6dff, #46c37b)" }}
              />
            </div>
            <p className="mt-1.5 text-xs text-mist/45">RBAC · TTL-72h · Anonymization · Audit trail</p>
          </div>

          {/* Peak zone */}
          <div className="rounded-[1.4rem] border border-warning/20 bg-warning/5 px-4 py-4">
            <p className="text-[10px] uppercase tracking-[0.22em] text-mist/45">Peak Density Zone</p>
            <p className="mt-2 text-lg font-semibold text-white">{data.peak_density_zone}</p>
            <p className="text-xs text-mist/55 mt-1">Avg density {(data.avg_crowd_density * 100).toFixed(0)}% · Monitor active</p>
          </div>

          {/* Alerts resolved */}
          <div className="rounded-[1.4rem] border border-safe/20 bg-safe/5 px-4 py-4">
            <p className="text-[10px] uppercase tracking-[0.22em] text-mist/45">Alerts Resolved Today</p>
            <p className="mt-2 text-lg font-semibold text-white">{data.alerts_resolved_today} alerts</p>
            <p className="text-xs text-mist/55 mt-1">Mean resolution time: 4.1 min · 100% resolved</p>
          </div>
        </div>
      </section>
    </div>
  );
}
