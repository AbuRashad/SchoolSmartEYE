import {
  Activity, LineChart, ShieldCheck, FileBarChart2, BellRing, LayoutGrid,
} from "lucide-react";
import type { NavPage } from "../types";

const navigation: { label: string; icon: typeof Activity; page: NavPage }[] = [
  { label: "Real-time Monitoring", icon: Activity, page: "dashboard" },
  { label: "SSI Deep Analysis", icon: LineChart, page: "ssi" },
  { label: "System Units", icon: LayoutGrid, page: "units" },
  { label: "Ministerial Reports", icon: FileBarChart2, page: "reports" },
  { label: "Parent Portal", icon: BellRing, page: "portal" },
];

type SidebarProps = {
  schoolName: string;
  status: "connected" | "reconnecting" | "offline";
  activePage: NavPage;
  onNavigate: (page: NavPage) => void;
};

export function Sidebar({ schoolName, status, activePage, onNavigate }: SidebarProps) {
  const statusTone =
    status === "connected" ? "bg-safe" : status === "reconnecting" ? "bg-warning" : "bg-critical";

  return (
    <aside className="flex min-h-screen w-full flex-col justify-between rounded-[2rem] border border-white/10 bg-panel px-6 py-8 text-mist shadow-panel lg:max-w-[280px]">
      <div className="space-y-8">
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="rounded-2xl bg-cobalt/20 p-3 text-sky">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <p className="text-xs uppercase tracking-[0.35em] text-mist/60">Campus Command</p>
          </div>
          <div>
            <h1 className="text-2xl font-semibold leading-tight">{schoolName}</h1>
            <p className="mt-2 text-sm text-mist/70">
              Intelligent school monitoring powered by 14 integrated units.
            </p>
          </div>
          <div className="flex items-center gap-3 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm">
            <span className={`h-2.5 w-2.5 rounded-full ${statusTone}`} />
            <span className="capitalize">WebSocket {status}</span>
          </div>
        </div>

        <nav className="space-y-2">
          {navigation.map((item, index) => {
            const Icon = item.icon;
            const isActive = activePage === item.page;
            return (
              <button
                key={item.label}
                type="button"
                onClick={() => onNavigate(item.page)}
                className={`flex w-full items-center justify-between rounded-2xl px-4 py-3 text-left text-sm transition ${
                  isActive
                    ? "bg-cobalt text-white"
                    : "text-mist/70 hover:bg-white/8 hover:text-white"
                }`}
              >
                <span className="flex items-center gap-3">
                  <Icon className="h-4 w-4" />
                  {item.label}
                </span>
                <span className="text-xs text-mist/45">0{index + 1}</span>
              </button>
            );
          })}
        </nav>
      </div>

      <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
        <p className="text-xs uppercase tracking-[0.28em] text-mist/50">Arab Governance (Unit 14)</p>
        <p className="mt-3 text-sm text-mist/75">
          All data is anonymized, TTL-enforced (72h), and RBAC-controlled per the Arab Data Governance Model.
        </p>
      </div>
    </aside>
  );
}
