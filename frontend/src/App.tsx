import { useState } from "react";
import { KpiGauge } from "./components/KpiGauge";
import { LiveAlertFeed } from "./components/LiveAlertFeed";
import { RiskHeatmap } from "./components/RiskHeatmap";
import { Sidebar } from "./components/Sidebar";
import { SSIHistoryChart } from "./components/SSIHistoryChart";
import { SSILivePanel } from "./components/SSILivePanel";
import { UnitsGrid } from "./components/UnitsGrid";
import { useSafetyDashboardSocket } from "./hooks/useSafetyDashboardSocket";
import { useSSILive, useSSIHistory, useUnits } from "./hooks/useSSIData";
import type { NavPage } from "./types";

export default function App() {
  const [page, setPage] = useState<NavPage>("dashboard");
  const snapshot = useSafetyDashboardSocket();
  const { data: ssiLive } = useSSILive();
  const ssiHistory = useSSIHistory();
  const units = useUnits();

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

              <div className="grid gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
                <KpiGauge value={snapshot.ssi} benchmark={snapshot.benchmark} />
                <LiveAlertFeed alerts={snapshot.liveAlerts} />
              </div>

              <RiskHeatmap cells={snapshot.heatmapCells} availableTimeSlots={snapshot.availableTimeSlots} />
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

          {/* ─── REPORTS PAGE ────────────────────────────────── */}
          {page === "reports" && (
            <section className="rounded-[2rem] border border-white/10 bg-panel/70 px-6 py-10 shadow-panel text-center">
              <p className="text-xs uppercase tracking-[0.28em] text-mist/50">Ministerial Reports</p>
              <h2 className="mt-3 text-2xl font-semibold text-white">Multi-Level Periodic Reports</h2>
              <p className="mt-4 text-sm text-mist/60 max-w-lg mx-auto">
                Operational, analytical, supervisory, and ministerial reports powered by Unit 11.
                Connect the backend to generate live semester summaries.
              </p>
              <div className="mt-8 grid gap-4 sm:grid-cols-3 max-w-2xl mx-auto">
                {["Operational Report", "School Analytics", "Ministerial Summary"].map((r) => (
                  <div key={r} className="rounded-[1.6rem] border border-white/10 bg-white/5 p-5">
                    <p className="text-sm font-medium text-white">{r}</p>
                    <p className="mt-2 text-xs text-mist/40">Available via /api/v1/ssi/history</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* ─── PARENT PORTAL PAGE ──────────────────────────── */}
          {page === "portal" && (
            <section className="rounded-[2rem] border border-white/10 bg-panel/70 px-6 py-10 shadow-panel text-center">
              <p className="text-xs uppercase tracking-[0.28em] text-mist/50">Parent Portal</p>
              <h2 className="mt-3 text-2xl font-semibold text-white">Smart Parent Portal — Unit 12</h2>
              <p className="mt-4 text-sm text-mist/60 max-w-lg mx-auto">
                Privacy-governed attendance & safety notifications for guardians. Powered by the Arab Data Governance Model (Unit 14).
              </p>
              <div className="mt-8 grid gap-4 sm:grid-cols-2 max-w-xl mx-auto">
                {[
                  { label: "Attendance Status", val: "Present ✓" },
                  { label: "Safety Status", val: "Safe ✓" },
                  { label: "Last Known Zone", val: "Learning Commons" },
                  { label: "Dismissal Status", val: "Not at exit gate" },
                ].map(({ label, val }) => (
                  <div key={label} className="rounded-[1.6rem] border border-white/10 bg-white/5 p-5 text-left">
                    <p className="text-xs uppercase tracking-[0.2em] text-mist/40">{label}</p>
                    <p className="mt-2 text-base font-semibold text-white">{val}</p>
                  </div>
                ))}
              </div>
              <p className="mt-6 text-xs text-mist/30">
                All data anonymized per POLICY.minor_age_threshold = 18. Video logs expire after 72h TTL.
              </p>
            </section>
          )}
        </main>
      </div>
    </div>
  );
}
