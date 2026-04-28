import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, Trash2, RefreshCw, BatteryLow, Radio, Watch } from "lucide-react";
import type {
  BraceletCreatePayload,
  BraceletRecord,
  StudentRecord,
  ZoneRecord,
} from "../../types";
import { api } from "./api";
import { Field, inputCls, type Flash } from "./ui";

export function BraceletsTab({ flash }: { flash: Flash }) {
  const [bracelets, setBracelets] = useState<BraceletRecord[]>([]);
  const [students, setStudents] = useState<StudentRecord[]>([]);
  const [zones, setZones] = useState<ZoneRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState<BraceletCreatePayload>({
    bracelet_id: "",
    student_id: "",
    mac_address: "",
    battery_level: 100,
    firmware_version: "1.0.0",
    notes: "",
    is_active: true,
  });

  const reload = useCallback(async () => {
    try {
      const [b, s, z] = await Promise.all([
        api<BraceletRecord[]>("/bracelets"),
        api<StudentRecord[]>("/students"),
        api<ZoneRecord[]>("/zones"),
      ]);
      setBracelets(b);
      setStudents(s);
      setZones(z);
    } catch (e) {
      flash("err", `Failed to load: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, [flash]);

  useEffect(() => {
    reload();
  }, [reload]);

  const unassigned = useMemo(() => {
    const assigned = new Set(bracelets.map((b) => b.student_id));
    return students.filter((s) => !assigned.has(s.student_id));
  }, [bracelets, students]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api<BraceletRecord>("/bracelets", {
        method: "POST",
        body: JSON.stringify(form),
      });
      flash("ok", `Bracelet ${form.bracelet_id} assigned`);
      setForm({
        bracelet_id: "",
        student_id: "",
        mac_address: "",
        battery_level: 100,
        firmware_version: "1.0.0",
        notes: "",
        is_active: true,
      });
      reload();
    } catch (e) {
      flash("err", (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const removeOne = async (id: string) => {
    if (!confirm(`Delete bracelet "${id}"?`)) return;
    setBusy(true);
    try {
      await api(`/bracelets/${encodeURIComponent(id)}`, { method: "DELETE" });
      flash("ok", `Bracelet ${id} removed`);
      reload();
    } catch (e) {
      flash("err", (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const pingOne = async (id: string) => {
    const zoneId = zones[0]?.zone_id;
    if (!zoneId) {
      flash("err", "No zones available");
      return;
    }
    setBusy(true);
    try {
      await api(`/bracelets/${encodeURIComponent(id)}/ping`, {
        method: "POST",
        body: JSON.stringify({
          zone_id: zoneId,
          battery_level: Math.max(5, Math.floor(Math.random() * 100)),
        }),
      });
      flash("ok", `Pinged ${id} at ${zoneId}`);
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
            Registered Bracelets
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
        ) : bracelets.length === 0 ? (
          <div className="rounded-2xl border border-white/10 bg-panel/60 px-4 py-8 text-center text-sm text-mist/70">
            <Watch className="mx-auto mb-2 h-8 w-8 text-mist/40" />
            No bracelets registered. Add one from the form →
          </div>
        ) : (
          <div className="overflow-hidden rounded-2xl border border-white/10 bg-panel/60">
            <table className="w-full text-sm">
              <thead className="bg-white/5 text-left text-[11px] uppercase tracking-wider text-mist/60">
                <tr>
                  <th className="px-3 py-2">ID</th>
                  <th className="px-3 py-2">Student</th>
                  <th className="px-3 py-2">MAC</th>
                  <th className="px-3 py-2">Battery</th>
                  <th className="px-3 py-2">Last Seen</th>
                  <th className="px-3 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {bracelets.map((b) => (
                  <tr key={b.bracelet_id} className="border-t border-white/5 align-top">
                    <td className="px-3 py-2 font-mono text-[11px] text-mist/80">
                      {b.bracelet_id}
                    </td>
                    <td className="px-3 py-2 text-white">
                      {b.student_name ?? (
                        <span className="italic text-mist/50">unknown</span>
                      )}
                      <div className="text-[10px] text-mist/50">{b.student_id}</div>
                    </td>
                    <td className="px-3 py-2 font-mono text-[11px] text-mist/70">
                      {b.mac_address}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-flex items-center gap-1 ${
                          b.low_battery ? "text-critical" : "text-mist/80"
                        }`}
                      >
                        {b.low_battery && <BatteryLow className="h-3 w-3" />}
                        {b.battery_level}%
                      </span>
                    </td>
                    <td className="px-3 py-2 text-xs text-mist/70">
                      {b.last_seen_zone ?? "—"}
                      <div className="text-[10px] text-mist/50">
                        {b.last_seen_at
                          ? new Date(b.last_seen_at).toLocaleTimeString()
                          : "never"}
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => pingOne(b.bracelet_id)}
                          disabled={busy}
                          title="Simulate heartbeat"
                          className="rounded-lg border border-cobalt/40 bg-cobalt/10 p-1.5 text-cobalt hover:bg-cobalt/20 disabled:opacity-50"
                        >
                          <Radio className="h-3.5 w-3.5" />
                        </button>
                        <button
                          type="button"
                          onClick={() => removeOne(b.bracelet_id)}
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

      <form
        onSubmit={submit}
        className="h-max space-y-3 rounded-2xl border border-white/10 bg-panel/60 p-5"
      >
        <h3 className="flex items-center gap-2 text-sm font-semibold text-white">
          <Plus className="h-4 w-4 text-cobalt" /> Register Bracelet
        </h3>
        <Field label="Bracelet ID">
          <input
            required
            value={form.bracelet_id}
            onChange={(e) => setForm({ ...form, bracelet_id: e.target.value.trim() })}
            placeholder="BR-0001"
            className={inputCls}
          />
        </Field>
        <Field
          label="Assign to Student"
          hint={
            unassigned.length === 0
              ? "All students already have bracelets. Add a new student first."
              : undefined
          }
        >
          <select
            required
            value={form.student_id}
            onChange={(e) => setForm({ ...form, student_id: e.target.value })}
            className={inputCls}
          >
            <option value="">— select student —</option>
            {unassigned.map((s) => (
              <option key={s.student_id} value={s.student_id}>
                {s.name} ({s.grade} {s.class_section})
              </option>
            ))}
          </select>
        </Field>
        <Field label="MAC Address" hint="Format AA:BB:CC:DD:EE:FF">
          <input
            required
            value={form.mac_address}
            onChange={(e) => setForm({ ...form, mac_address: e.target.value.trim() })}
            placeholder="AA:BB:CC:DD:EE:FF"
            className={inputCls}
          />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Battery %">
            <input
              type="number"
              min={0}
              max={100}
              value={form.battery_level ?? 100}
              onChange={(e) =>
                setForm({ ...form, battery_level: Number(e.target.value) })
              }
              className={inputCls}
            />
          </Field>
          <Field label="Firmware">
            <input
              value={form.firmware_version ?? ""}
              onChange={(e) => setForm({ ...form, firmware_version: e.target.value })}
              placeholder="1.0.0"
              className={inputCls}
            />
          </Field>
        </div>
        <Field label="Notes">
          <input
            value={form.notes ?? ""}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
            placeholder="Optional"
            className={inputCls}
          />
        </Field>
        <button
          type="submit"
          disabled={busy || unassigned.length === 0}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-cobalt px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-cobalt/90 disabled:opacity-50"
        >
          <Plus className="h-4 w-4" /> Register Bracelet
        </button>
      </form>
    </div>
  );
}
