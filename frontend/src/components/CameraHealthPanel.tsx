import { useCallback, useEffect, useState } from "react";
import { Activity, AlertTriangle, Camera, RefreshCw } from "lucide-react";
import type { LiveCameraInfo } from "../types";
import { api } from "./control/api";

type HealthStatus = "online" | "degraded" | "offline" | "stalled";
type HealthSnapshot = {
  id: number;
  camera_id: string;
  status: HealthStatus;
  observed_at: string;
  last_seen_at: string;
  fps: number;
  latency_ms: number;
  consecutive_missed_heartbeats: number;
  reconnect_count: number;
  frozen_frame: boolean;
  source: string;
};
type HealthHistory = { items: HealthSnapshot[]; count: number };

const statusStyles: Record<HealthStatus, string> = {
  online: "bg-safe/15 text-safe border-safe/30",
  degraded: "bg-warning/15 text-warning border-warning/30",
  offline: "bg-critical/15 text-critical border-critical/30",
  stalled: "bg-violet-400/15 text-violet-200 border-violet-300/30",
};

export function CameraHealthPanel() {
  const [rows, setRows] = useState<Array<{ camera: LiveCameraInfo; health: HealthSnapshot | null }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      const cameras = await api<LiveCameraInfo[]>("/cameras");
      const results = await Promise.all(cameras.map(async (camera) => {
        try {
          const history = await api<HealthHistory>(`/camera-health/${encodeURIComponent(camera.camera_id)}?limit=1`);
          return { camera, health: history.items[0] ?? null };
        } catch {
          return { camera, health: null };
        }
      }));
      setRows(results);
      setError(null);
    } catch (e) {
      setError((e as Error).message || "Unable to load camera health");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
    const timer = window.setInterval(() => void reload(), 10000);
    return () => window.clearInterval(timer);
  }, [reload]);

  return (
    <section className="space-y-4 rounded-[2rem] border border-white/10 bg-panel/70 p-6 shadow-panel">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.25em] text-mist/50">Camera Event Intelligence</p>
          <h3 className="mt-2 text-xl font-semibold text-white">Camera Health Monitor</h3>
          <p className="mt-1 text-sm text-mist/65">Latest persisted operational telemetry for cameras registered to this school.</p>
        </div>
        <button type="button" onClick={() => void reload()} className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs text-mist/80 hover:bg-white/10">
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </button>
      </div>

      <div className="rounded-xl border border-sky-300/20 bg-sky-300/5 px-4 py-3 text-xs leading-relaxed text-sky-100/80">
        Telemetry-only view: status is classified from reported metrics. This panel does not analyse people or video frames.
        Until a trusted edge-agent is connected, snapshots must be submitted by an authorised school principal.
      </div>

      {loading ? (
        <div className="py-8 text-center text-sm text-mist/60">Loading camera health history…</div>
      ) : error ? (
        <div className="flex items-center gap-2 rounded-xl border border-critical/30 bg-critical/10 p-4 text-sm text-critical">
          <AlertTriangle className="h-4 w-4" /> {error}
        </div>
      ) : rows.length === 0 ? (
        <div className="py-8 text-center text-sm text-mist/60">
          <Camera className="mx-auto mb-2 h-7 w-7 opacity-50" /> No registered cameras are available for this school.
        </div>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {rows.map(({ camera, health }) => (
            <article key={camera.camera_id} className="rounded-2xl border border-white/10 bg-black/10 p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-white">{camera.label}</p>
                  <p className="mt-1 font-mono text-[11px] text-mist/50">{camera.camera_id} · {camera.zone_id}</p>
                </div>
                {health ? (
                  <span className={`shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase ${statusStyles[health.status]}`}>{health.status}</span>
                ) : (
                  <span className="shrink-0 rounded-full border border-white/15 bg-white/5 px-2.5 py-1 text-[11px] text-mist/60">No telemetry</span>
                )}
              </div>
              {health ? (
                <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
                  <Metric label="Frame rate" value={`${health.fps.toFixed(1)} FPS`} />
                  <Metric label="Latency" value={`${health.latency_ms.toFixed(0)} ms`} />
                  <Metric label="Missed heartbeats" value={health.consecutive_missed_heartbeats.toString()} />
                  <Metric label="Reconnects" value={health.reconnect_count.toString()} />
                  <div className="col-span-2 flex items-center gap-2 border-t border-white/5 pt-3 text-mist/50">
                    <Activity className="h-3.5 w-3.5" />
                    Last seen {new Date(health.last_seen_at).toLocaleString()} · {health.source.replace(/_/g, " ")}
                  </div>
                </div>
              ) : (
                <p className="mt-4 text-xs text-mist/50">No health snapshot has been recorded for this camera yet. No live health status is assumed.</p>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white/[0.035] p-3">
      <p className="text-[10px] uppercase tracking-wider text-mist/45">{label}</p>
      <p className="mt-1 font-semibold tabular-nums text-white">{value}</p>
    </div>
  );
}
