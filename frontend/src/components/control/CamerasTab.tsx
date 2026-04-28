import { useCallback, useEffect, useState } from "react";
import { Camera, Plus, Play, Square, Trash2, RefreshCw } from "lucide-react";
import type { CameraCreatePayload, LiveCameraInfo, ZoneRecord } from "../../types";
import { api } from "./api";
import { Field, inputCls, type Flash } from "./ui";

export function CamerasTab({ flash }: { flash: Flash }) {
  const [cameras, setCameras] = useState<LiveCameraInfo[]>([]);
  const [zones, setZones] = useState<ZoneRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState<CameraCreatePayload>({
    camera_id: "",
    zone_id: "",
    label: "",
    source_url: "",
    anonymize_faces: true,
  });

  const reload = useCallback(async () => {
    try {
      const [cams, zs] = await Promise.all([
        api<LiveCameraInfo[]>("/cameras"),
        api<ZoneRecord[]>("/zones"),
      ]);
      setCameras(cams);
      setZones(zs);
    } catch (e) {
      flash("err", `Failed to load: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, [flash]);

  useEffect(() => {
    reload();
    const id = window.setInterval(reload, 5000);
    return () => window.clearInterval(id);
  }, [reload]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api<LiveCameraInfo>("/cameras", { method: "POST", body: JSON.stringify(form) });
      flash("ok", `Camera ${form.camera_id} registered`);
      setForm({ camera_id: "", zone_id: "", label: "", source_url: "", anonymize_faces: true });
      reload();
    } catch (e) {
      flash("err", (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const doAction = async (id: string, action: "start" | "stop" | "delete") => {
    setBusy(true);
    try {
      if (action === "delete") {
        await api(`/cameras/${encodeURIComponent(id)}`, { method: "DELETE" });
        flash("ok", `Camera ${id} removed`);
      } else {
        await api(`/cameras/${encodeURIComponent(id)}/${action}`, { method: "POST" });
        flash("ok", `Camera ${id} ${action}ed`);
      }
      reload();
    } catch (e) {
      flash("err", (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_420px]">
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold uppercase tracking-[0.2em] text-mist/60">
            Registered Cameras
          </h3>
          <button
            type="button"
            onClick={reload}
            disabled={busy}
            className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-mist/80 hover:bg-white/10 hover:text-white disabled:opacity-50"
          >
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </button>
        </div>

        {loading ? (
          <div className="rounded-2xl border border-white/10 bg-panel/60 px-4 py-8 text-center text-sm text-mist/60">
            Loading…
          </div>
        ) : cameras.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-panel/60 px-4 py-8 text-center text-sm text-mist/70">
            <Camera className="mx-auto mb-2 h-8 w-8 text-mist/40" />
            No cameras registered yet. Use the form on the right.
          </div>
        ) : (
          <div className="overflow-hidden rounded-2xl border border-white/10 bg-panel/60">
            <table className="w-full text-sm">
              <thead className="bg-white/5 text-left text-[11px] uppercase tracking-wider text-mist/60">
                <tr>
                  <th className="px-3 py-2">ID</th>
                  <th className="px-3 py-2">Label</th>
                  <th className="px-3 py-2">Zone</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Frames</th>
                  <th className="px-3 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {cameras.map((c) => (
                  <tr key={c.camera_id} className="border-t border-white/5 align-top">
                    <td className="px-3 py-2 font-mono text-[11px] text-mist/80">{c.camera_id}</td>
                    <td className="px-3 py-2 text-white">{c.label}</td>
                    <td className="px-3 py-2 text-mist/70">{c.zone_id}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[11px] ${
                          c.status === "active"
                            ? "bg-safe/20 text-safe"
                            : c.status === "degraded"
                            ? "bg-warning/20 text-warning"
                            : "bg-critical/20 text-critical"
                        }`}
                      >
                        {c.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-mist/75">
                      {c.total_frames_captured.toLocaleString()}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex justify-end gap-1">
                        {c.is_running ? (
                          <button
                            type="button"
                            onClick={() => doAction(c.camera_id, "stop")}
                            disabled={busy}
                            title="Stop"
                            className="rounded-lg border border-warning/40 bg-warning/10 p-1.5 text-warning hover:bg-warning/20 disabled:opacity-50"
                          >
                            <Square className="h-3.5 w-3.5" />
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={() => doAction(c.camera_id, "start")}
                            disabled={busy}
                            title="Start"
                            className="rounded-lg border border-safe/40 bg-safe/10 p-1.5 text-safe hover:bg-safe/20 disabled:opacity-50"
                          >
                            <Play className="h-3.5 w-3.5" />
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => {
                            if (confirm(`Remove camera "${c.camera_id}"?`))
                              doAction(c.camera_id, "delete");
                          }}
                          disabled={busy}
                          title="Delete"
                          className="rounded-lg border border-critical/40 bg-critical/10 p-1.5 text-critical hover:bg-critical/20 disabled:opacity-50"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <form onSubmit={submit} className="h-max space-y-3 rounded-2xl border border-white/10 bg-panel/60 p-5">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-white">
          <Plus className="h-4 w-4 text-cobalt" /> Add Camera
        </h3>
        <Field label="Camera ID" hint="Unique short id, e.g. cam-gate">
          <input
            required
            value={form.camera_id}
            onChange={(e) => setForm({ ...form, camera_id: e.target.value.trim() })}
            placeholder="cam-gate"
            className={inputCls}
          />
        </Field>
        <Field label="Zone">
          <select
            required
            value={form.zone_id}
            onChange={(e) => setForm({ ...form, zone_id: e.target.value })}
            className={inputCls}
          >
            <option value="">— select zone —</option>
            {zones.map((z) => (
              <option key={z.zone_id} value={z.zone_id}>
                {z.label} ({z.zone_id})
              </option>
            ))}
          </select>
        </Field>
        <Field label="Display Label">
          <input
            required
            value={form.label}
            onChange={(e) => setForm({ ...form, label: e.target.value })}
            placeholder="Main Gate — Entry"
            className={inputCls}
          />
        </Field>
        <Field label="Source URL" hint="rtsp://…, http://…/video.mjpg, '0' (USB), or ./path/file.mp4">
          <input
            required
            value={form.source_url}
            onChange={(e) => setForm({ ...form, source_url: e.target.value })}
            placeholder="rtsp://admin:pwd@192.168.1.50:554/Streaming/Channels/101"
            className={inputCls}
          />
        </Field>
        <label className="flex items-center gap-2 text-sm text-mist/80">
          <input
            type="checkbox"
            checked={form.anonymize_faces}
            onChange={(e) => setForm({ ...form, anonymize_faces: e.target.checked })}
            className="h-4 w-4 rounded border-white/20 bg-white/10 text-cobalt"
          />
          Apply Unit 14 face anonymization (recommended)
        </label>
        <button
          type="submit"
          disabled={busy}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-cobalt px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-cobalt/90 disabled:opacity-50"
        >
          <Plus className="h-4 w-4" /> Register & Start
        </button>
      </form>
    </div>
  );
}
