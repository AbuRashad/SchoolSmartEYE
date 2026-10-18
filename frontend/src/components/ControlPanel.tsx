import { useCallback, useState } from "react";
import {
  Camera, Users, Watch, Settings as SettingsIcon,
  AlertTriangle, CheckCircle2,
} from "lucide-react";
import { CamerasTab } from "./control/CamerasTab";
import { BraceletsTab } from "./control/BraceletsTab";
import { StudentsTab } from "./control/StudentsTab";
import { SettingsTab } from "./control/SettingsTab";
import type { Flash } from "./control/ui";

type Tab = "cameras" | "bracelets" | "students" | "settings";

const TABS: { id: Tab; label: string; icon: typeof Camera }[] = [
  { id: "cameras", label: "Cameras", icon: Camera },
  { id: "bracelets", label: "Bracelets", icon: Watch },
  { id: "students", label: "Students", icon: Users },
  { id: "settings", label: "Advanced Settings", icon: SettingsIcon },
];

export function ControlPanel() {
  const [tab, setTab] = useState<Tab>("cameras");
  const [toast, setToast] = useState<{ kind: "ok" | "err"; message: string } | null>(null);

  const flash: Flash = useCallback((kind, message) => {
    setToast({ kind, message });
    window.setTimeout(() => setToast(null), 4000);
  }, []);

  return (
    <section className="space-y-4">
      <header className="rounded-[2rem] border border-white/10 bg-panel/70 px-6 py-5 shadow-panel">
        <p className="text-xs uppercase tracking-[0.28em] text-mist/50">System Control</p>
        <h2 className="mt-2 text-2xl font-semibold text-white">Control Panel</h2>
        <p className="mt-2 text-sm text-mist/75">
          Add and manage cameras, register student bracelets, enroll students, and tune advanced runtime
          settings. All changes take effect live — no restart required.
        </p>
      </header>

      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => {
          const Icon = t.icon;
          const active = t.id === tab;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-2 rounded-2xl border px-4 py-2 text-sm transition ${
                active
                  ? "border-cobalt bg-cobalt text-white"
                  : "border-white/10 bg-white/5 text-mist/80 hover:bg-white/10 hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4" />
              {t.label}
            </button>
          );
        })}
      </div>

      {toast && (
        <div
          className={`rounded-2xl border px-4 py-3 text-sm ${
            toast.kind === "ok"
              ? "border-safe/40 bg-safe/10 text-safe"
              : "border-critical/40 bg-critical/10 text-critical"
          }`}
        >
          {toast.kind === "ok" ? (
            <CheckCircle2 className="mr-2 inline h-4 w-4" />
          ) : (
            <AlertTriangle className="mr-2 inline h-4 w-4" />
          )}
          {toast.message}
        </div>
      )}

      {tab === "cameras" && <CamerasTab flash={flash} />}
      {tab === "bracelets" && <BraceletsTab flash={flash} />}
      {tab === "students" && <StudentsTab flash={flash} />}
      {tab === "settings" && <SettingsTab flash={flash} />}
    </section>
  );
}
