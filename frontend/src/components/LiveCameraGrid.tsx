import { useEffect, useState } from "react";
import { Camera, RefreshCw, AlertTriangle, CircleDot } from "lucide-react";
import type { LiveCameraInfo } from "../types";

const REFRESH_MS = 5000;

export function LiveCameraGrid() {
  const [cameras, setCameras] = useState<LiveCameraInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0); // forces <img> reloads if connection drops

  // Periodic status refresh
  useEffect(() => {
    let cancelled = false;
    const load = () => {
      fetch("/api/v1/cameras")
        .then((r) => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json() as Promise<LiveCameraInfo[]>;
        })
        .then((d) => {
          if (cancelled) return;
          setCameras(d);
          setError(null);
        })
        .catch((e) => {
          if (cancelled) return;
          setError(e.message ?? "Failed to load cameras");
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    };
    load();
    const id = window.setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  if (loading) {
    return (
      <div className="rounded-[2rem] border border-white/10 bg-panel/70 px-6 py-12 text-center text-mist/60 shadow-panel">
        Connecting to camera service…
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-[2rem] border border-critical/35 bg-critical/10 px-6 py-8 text-center text-mist/80 shadow-panel">
        <AlertTriangle className="mx-auto mb-3 h-8 w-8 text-critical" />
        Camera service unreachable: {error}
      </div>
    );
  }

  if (cameras.length === 0) {
    return (
      <div className="rounded-[2rem] border border-white/10 bg-panel/70 px-6 py-12 text-center text-mist/70 shadow-panel">
        <Camera className="mx-auto mb-4 h-10 w-10 text-mist/40" />
        <h3 className="text-lg font-semibold text-white">No live cameras configured</h3>
        <p className="mx-auto mt-2 max-w-xl text-sm text-mist/65">
          To connect real school cameras, create a <code className="rounded bg-white/10 px-1">cameras.json</code> file at the
          project root listing your RTSP/HTTP/USB sources, then restart the backend. See{" "}
          <code className="rounded bg-white/10 px-1">cameras.example.json</code> for a template.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-mist/70">
          {cameras.length} live camera{cameras.length === 1 ? "" : "s"} connected — face anonymization is enforced by Unit 14.
        </p>
        <button
          type="button"
          onClick={() => setTick((t) => t + 1)}
          className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-mist/80 hover:bg-white/10"
        >
          <RefreshCw className="h-3.5 w-3.5" /> Reload streams
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {cameras.map((cam) => (
          <CameraTile key={cam.camera_id} cam={cam} reloadKey={tick} />
        ))}
      </div>
    </div>
  );
}

function CameraTile({ cam, reloadKey }: { cam: LiveCameraInfo; reloadKey: number }) {
  const [imgError, setImgError] = useState(false);

  const statusColor =
    cam.status === "active"
      ? "bg-safe"
      : cam.status === "degraded"
      ? "bg-warning"
      : "bg-critical";

  const isLive = cam.status === "active" && cam.is_running && !imgError;

  return (
    <div className="overflow-hidden rounded-2xl border border-white/10 bg-panel shadow-panel">
      <div className="relative aspect-video bg-black/50">
        {isLive ? (
          <img
            key={`${cam.camera_id}-${reloadKey}`}
            src={`/api/v1/cameras/${cam.camera_id}/stream.mjpg?cb=${reloadKey}`}
            alt={cam.label}
            className="h-full w-full object-contain"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="flex h-full w-full flex-col items-center justify-center text-center text-mist/60">
            <AlertTriangle className="mb-2 h-8 w-8 text-warning" />
            <p className="text-sm font-medium text-white">
              {cam.status === "offline" ? "Camera offline" : "Connecting…"}
            </p>
            {cam.last_error && (
              <p className="mt-1 max-w-[80%] truncate text-[11px] text-mist/55" title={cam.last_error}>
                {cam.last_error}
              </p>
            )}
          </div>
        )}
        <div className="absolute left-3 top-3 flex items-center gap-2 rounded-full bg-black/60 px-3 py-1 text-[11px] text-white backdrop-blur">
          <span className={`h-2 w-2 rounded-full ${statusColor}`} />
          <span className="capitalize">{cam.status}</span>
          {isLive && <CircleDot className="h-3 w-3 text-critical" />}
        </div>
      </div>

      <div className="space-y-1 px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <h3 className="truncate text-sm font-semibold text-white" title={cam.label}>
            {cam.label}
          </h3>
          <span className="shrink-0 text-[10px] uppercase tracking-wider text-mist/50">{cam.camera_id}</span>
        </div>
        <p className="truncate text-xs text-mist/60" title={cam.source_url}>
          {cam.source_url}
        </p>
        <div className="flex items-center justify-between text-[11px] text-mist/55">
          <span>Frames: {cam.total_frames_captured.toLocaleString()}</span>
          <span>Drop: {(cam.drop_rate * 100).toFixed(1)}%</span>
          {cam.anonymize_faces && (
            <span className="rounded bg-cobalt/20 px-1.5 py-0.5 text-cobalt">🛡 Face blur</span>
          )}
        </div>
      </div>
    </div>
  );
}
