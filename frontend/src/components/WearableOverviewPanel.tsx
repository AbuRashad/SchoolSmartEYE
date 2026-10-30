import { useCallback, useEffect, useState } from "react";
import { Activity, AlertTriangle, RefreshCw, ShieldCheck, Watch } from "lucide-react";
import { api } from "./control/api";

type WearableOverview = {
  status: "available" | "suppressed";
  coverage_percent: number | null;
  reporting_devices: number | null;
  reporting_window_hours: number;
  minimum_cohort_size: number;
  message: string;
  data_status: "live_unverified";
  human_review_required: boolean;
};

export function WearableOverviewPanel() {
  const [overview, setOverview] = useState<WearableOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const result = await api<WearableOverview>("/wearables/overview");
      setOverview(result);
      setError(null);
    } catch (e) {
      setError((e as Error).message || "Unable to load WAI overview");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
    const timer = window.setInterval(() => void reload(), 30000);
    return () => window.clearInterval(timer);
  }, [reload]);

  return (
    <section className="space-y-4 rounded-[2rem] border border-white/10 bg-panel/70 p-6 shadow-panel">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-mist/50">WAI Wearable Intelligence</p>
          <h3 className="mt-2 flex items-center gap-2 text-xl font-semibold text-white">
            <Watch className="h-5 w-5 text-sky-200" /> Smart Band Fleet Overview
          </h3>
          <p className="mt-1 text-sm text-mist/65">School-level device reporting coverage · last {overview?.reporting_window_hours ?? 24} hours</p>
        </div>
        <button type="button" onClick={() => void reload()} className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-mist/80 hover:bg-white/10">
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </button>
      </div>

      <div className="flex items-start gap-3 rounded-xl border border-sky-300/20 bg-sky-300/5 px-4 py-3 text-xs leading-relaxed text-sky-100/80">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
        <p>Privacy protection: this panel shows device coverage only. Individual heart-rate, HRV, temperature, activity, and EDA readings are not displayed or sent to the six-agent review.</p>
      </div>

      {loading ? (
        <div className="py-8 text-center text-sm text-mist/60">Loading WAI device coverage…</div>
      ) : error ? (
        <div className="flex items-center gap-2 rounded-xl border border-critical/30 bg-critical/10 p-4 text-sm text-critical">
          <AlertTriangle className="h-4 w-4" /> {error}
        </div>
      ) : overview?.status === "available" ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-2xl border border-white/10 bg-black/10 p-4">
            <p className="text-xs uppercase tracking-wider text-mist/45">Reporting coverage</p>
            <p className="mt-2 text-3xl font-semibold tabular-nums text-white">{overview.coverage_percent?.toFixed(1)}%</p>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10">
              <div className="h-full rounded-full bg-sky-300" style={{ width: `${Math.min(100, Math.max(0, overview.coverage_percent ?? 0))}%` }} />
            </div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-black/10 p-4">
            <p className="text-xs uppercase tracking-wider text-mist/45">Reporting devices</p>
            <p className="mt-2 text-3xl font-semibold tabular-nums text-white">{overview.reporting_devices}</p>
            <p className="mt-2 text-xs text-mist/50">Distinct devices with accepted observations in the reporting window</p>
          </div>
        </div>
      ) : (
        <div className="flex items-start gap-3 rounded-2xl border border-warning/25 bg-warning/5 p-4">
          <Activity className="mt-0.5 h-5 w-5 shrink-0 text-warning" />
          <div>
            <p className="text-sm font-semibold text-white">Coverage is privacy-suppressed</p>
            <p className="mt-1 text-xs leading-relaxed text-mist/65">{overview?.message ?? "Waiting for WAI coverage data."}</p>
          </div>
        </div>
      )}

      <p className="text-[11px] leading-relaxed text-mist/45">
        Source status: {overview?.data_status ?? "unknown"} · {overview?.human_review_required ? "Human review required" : "No automated action"}.
        This is device telemetry, not a health assessment or confirmation that a physical WAI sensor is clinically validated.
      </p>
    </section>
  );
}
