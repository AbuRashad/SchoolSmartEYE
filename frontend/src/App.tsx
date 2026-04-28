import { useState } from "react";
import { Users, Activity, Calendar, Camera } from "lucide-react";
import { AIInsightsPanel } from "./components/AIInsightsPanel";
import { AnalyticsDashboard } from "./components/AnalyticsDashboard";
import { KpiGauge } from "./components/KpiGauge";
import { LiveAlertFeed } from "./components/LiveAlertFeed";
import { LiveCameraGrid } from "./components/LiveCameraGrid";
import { MetricCard } from "./components/MetricCard";
import { ControlPanel } from "./components/ControlPanel";
import { ParentPortalFull } from "./components/ParentPortalFull";
import { ReportsDashboard } from "./components/ReportsDashboard";
import { RiskHeatmap } from "./components/RiskHeatmap";
import { Sidebar } from "./components/Sidebar";
import { SSIHistoryChart } from "./components/SSIHistoryChart";
import { SSILivePanel } from "./components/SSILivePanel";
import { UnitsGrid } from "./components/UnitsGrid";
import { useSafetyDashboardSocket } from "./hooks/useSafetyDashboardSocket";
import { useSSILive, useSSIHistory, useUnits, useAnalyticsOverview, useReportsList, useReportsStats, useStudentPortal } from "./hooks/useSSIData";
import type { NavPage } from "./types";

export default function App() {
  const [page, setPage] = useState<NavPage>("dashboard");
  const snapshot = useSafetyDashboardSocket();
  const { data: ssiLive } = useSSILive();
  const ssiHistory = useSSIHistory();
  const units = useUnits();
  const { data: analytics } = useAnalyticsOverview();
  const reports = useReportsList();
  const reportStats = useReportsStats();
  const studentData = useStudentPortal();

  return (
    <div className="min-h-screen bg-academic px-4 py-4 text-white lg:px-6 lg:py-6">
      <div className="mx-auto grid max-w-[1680px] gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
        <Sidebar
          schoolName={snapshot.schoolName}
          status={snapshot.websocketStatus}
          activePage={page}
          onNavigate={setPage}
        />

        <main className="grid gap-4 content-start">
          {/* Backend error banner */}
          {!snapshot.fetchedFromBackend && snapshot.backendError && (
            <section className="rounded-[2rem] border border-critical/35 bg-critical/10 px-6 py-5 shadow-panel">
              <p className="text-xs uppercase tracking-[0.28em] text-white/70">Backend Status</p>
              <h2 className="mt-2 text-xl font-semibold text-white">Dashboard Disconnected</h2>
              <p className="mt-2 text-sm text-white/82">{snapshot.backendError}</p>
            </section>
          )}

          {/* ─── DASHBOARD PAGE ──────────────────────────────── */}
          {page === "dashboard" && (
            <>
              <section className="rounded-[2rem] border border-white/10 bg-panel/70 px-6 py-5 shadow-panel">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.28em] text-mist/50">Dashboard</p>
                    <h2 className="mt-2 text-2xl font-semibold text-white">Real-time Monitoring & Predictive Analysis</h2>
                    <p className="mt-2 text-sm text-mist/75">
                      {snapshot.fetchedFromBackend
                        ? "Live backend payloads connected to the operational dashboard."
                        : "Waiting for a healthy backend connection before rendering live operational data."}
                    </p>
                  </div>
                  <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-mist/80">
                    National benchmark {snapshot.benchmark}
                  </div>
                </div>
              </section>

              {/* Analytics metric row */}
              {analytics && (
                <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                  <MetricCard title="Total Students" value={analytics.total_students.toLocaleString()} subtitle="Enrolled & tracked" icon={Users} color="blue" trend="stable" trendValue="No change" />
                  <MetricCard title="Attendance Rate" value={`${analytics.attendance_rate.toFixed(1)}%`} subtitle="Today's attendance" icon={Calendar} color="green" trend="up" trendValue="+1.2%" />
                  <MetricCard title="Active Cameras" value={analytics.active_cameras} subtitle={`of ${analytics.total_units * 2} cameras`} icon={Camera} color="blue" trend="stable" trendValue="Nominal" />
                  <MetricCard title="System Uptime" value={`${analytics.uptime_percent.toFixed(1)}%`} subtitle="30-day SLA" icon={Activity} color="green" trend="up" trendValue="SLA OK" />
                </div>
              )}

              <div className="grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
                <KpiGauge value={snapshot.ssi} benchmark={snapshot.benchmark} />
                <LiveAlertFeed alerts={snapshot.liveAlerts} />
              </div>

              <RiskHeatmap cells={snapshot.heatmapCells} availableTimeSlots={snapshot.availableTimeSlots} />

              <AIInsightsPanel ssi={snapshot.ssi} benchmark={snapshot.benchmark} alerts={snapshot.liveAlerts} />
            </>
          )}

          {/* ─── SSI ANALYSIS PAGE ───────────────────────────── */}
          {page === "ssi" && (
            <>
              <section className="rounded-[2rem] border border-white/10 bg-panel/70 px-6 py-5 shadow-panel">
                <p className="text-xs uppercase tracking-[0.28em] text-mist/50">Analysis</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">School Safety Index — Deep Analysis</h2>
                <p className="mt-2 text-sm text-mist/75">
                  Real-time SSI computed from Units 05, 06, 07 & 08 signals via weighted composite formula.
                </p>
              </section>

              {ssiLive ? (
                <SSILivePanel data={ssiLive} />
              ) : (
                <div className="rounded-[2rem] border border-white/10 bg-panel/70 px-6 py-8 text-center text-mist/50 shadow-panel">
                  Connecting to SSI live endpoint…
                </div>
              )}

              {ssiHistory ? (
                <SSIHistoryChart
                  scores={ssiHistory.scores}
                  benchmark={ssiHistory.benchmark}
                  average={ssiHistory.average}
                  trend={ssiHistory.trend}
                />
              ) : (
                <div className="rounded-[2rem] border border-white/10 bg-panel/70 px-6 py-8 text-center text-mist/50 shadow-panel">
                  Loading 30-day history…
                </div>
              )}
            </>
          )}

          {/* ─── UNITS PAGE ──────────────────────────────────── */}
          {page === "units" && (
            <>
              <section className="rounded-[2rem] border border-white/10 bg-panel/70 px-6 py-5 shadow-panel">
                <p className="text-xs uppercase tracking-[0.28em] text-mist/50">System</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">14 Integrated Operational Units</h2>
                <p className="mt-2 text-sm text-mist/75">
                  Each unit is an independent, interconnected module contributing to the School Safety Index and Governance Layer.
                </p>
              </section>
              <UnitsGrid units={units.length > 0 ? units : Array.from({ length: 14 }, (_, i) => ({
                unit_id: i + 1,
                name: `Unit ${i + 1}`,
                category: "—",
                status: "active" as const,
              }))} />
            </>
          )}

          {/* ─── ANALYTICS PAGE ──────────────────────────────── */}
          {page === "analytics" && (
            <>
              <section className="rounded-[2rem] border border-white/10 bg-panel/70 px-6 py-5 shadow-panel">
                <p className="text-xs uppercase tracking-[0.28em] text-mist/50">Analytics</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">System Analytics Overview</h2>
                <p className="mt-2 text-sm text-mist/75">
                  Comprehensive performance metrics across attendance, security, cameras, and governance compliance.
                </p>
              </section>
              <AnalyticsDashboard data={analytics} />
            </>
          )}

          {/* ─── REPORTS PAGE ────────────────────────────────── */}
          {page === "reports" && (
            <>
              <section className="rounded-[2rem] border border-white/10 bg-panel/70 px-6 py-5 shadow-panel">
                <p className="text-xs uppercase tracking-[0.28em] text-mist/50">Reports</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">Multi-Level Periodic Reports</h2>
                <p className="mt-2 text-sm text-mist/75">
                  Operational, analytical, supervisory, and ministerial reports powered by Unit 11.
                </p>
              </section>
              <ReportsDashboard reports={reports} stats={reportStats} />
            </>
          )}

          {/* ─── LIVE CAMERAS PAGE ───────────────────────────── */}
          {page === "cameras" && (
            <>
              <section className="rounded-[2rem] border border-white/10 bg-panel/70 px-6 py-5 shadow-panel">
                <p className="text-xs uppercase tracking-[0.28em] text-mist/50">Live Cameras</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">Real Camera Feeds — Unit 01</h2>
                <p className="mt-2 text-sm text-mist/75">
                  Live RTSP / HTTP / USB camera streams from across the campus. All faces are blurred in real time by the
                  Arab Data Governance Layer (Unit 14) before any frame is shown or stored.
                </p>
              </section>
              <LiveCameraGrid />
            </>
          )}

          {/* ─── PARENT PORTAL PAGE ──────────────────────────── */}
          {page === "portal" && (
            <>
              <section className="rounded-[2rem] border border-white/10 bg-panel/70 px-6 py-5 shadow-panel">
                <p className="text-xs uppercase tracking-[0.28em] text-mist/50">Parent Portal</p>
                <h2 className="mt-2 text-2xl font-semibold text-white">Smart Parent Portal — Unit 12</h2>
                <p className="mt-2 text-sm text-mist/75">
                  Privacy-governed attendance & safety notifications for guardians. Powered by the Arab Data Governance Model (Unit 14).
                </p>
              </section>
              <ParentPortalFull data={studentData} />
            </>
          )}

          {/* ─── CONTROL PANEL PAGE ──────────────────────────── */}
          {page === "control" && <ControlPanel />}
        </main>
      </div>
    </div>
  );
}
