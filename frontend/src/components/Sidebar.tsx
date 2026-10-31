import {
  Activity, LineChart, ShieldCheck, FileBarChart2, BellRing, LayoutGrid, BarChart3, Camera, Settings, LogOut,
} from "lucide-react";
import { useAuth } from "../AuthContext";
import type { Role } from "../auth";
import type { NavPage } from "../types";

const navigation: { label: string; icon: typeof Activity; page: NavPage; minRole?: Role; group: string }[] = [
  { label: "Real-time Monitoring", icon: Activity, page: "dashboard", group: "Command Center" },
  { label: "Live Cameras", icon: Camera, page: "cameras", group: "Command Center" },
  { label: "SSI Deep Analysis", icon: LineChart, page: "ssi", group: "Intelligence" },
  { label: "System Units", icon: LayoutGrid, page: "units", group: "Intelligence" },
  { label: "Analytics Overview", icon: BarChart3, page: "analytics", group: "Intelligence" },
  { label: "Ministerial Reports", icon: FileBarChart2, page: "reports", minRole: "ministry", group: "Governance" },
  { label: "Parent Portal", icon: BellRing, page: "portal", group: "Governance" },
  { label: "Control Panel", icon: Settings, page: "control", group: "Administration" },
];

type SidebarProps = {
  schoolName: string;
  status: "connected" | "reconnecting" | "offline";
  activePage: NavPage;
  onNavigate: (page: NavPage) => void;
};

export function Sidebar({ schoolName, status, activePage, onNavigate }: SidebarProps) {
  const { user, logout, can } = useAuth();
  const visibleNavigation = navigation.filter((item) => !item.minRole || can(item.minRole));
  const groups = [...new Set(visibleNavigation.map((item) => item.group))];
  const statusTone = status === "connected" ? "bg-safe" : status === "reconnecting" ? "bg-warning" : "bg-critical";
  const statusLabel = status === "connected" ? "Connected" : status === "reconnecting" ? "Reconnecting" : "Offline";

  return (
    <aside className="flex min-h-[calc(100vh-3rem)] w-full flex-col justify-between overflow-hidden rounded-[1.75rem] border border-panel-border bg-[#111d30]/95 px-5 py-6 text-mist shadow-panel backdrop-blur-xl lg:sticky lg:top-6 lg:max-w-[280px]">
      <div className="space-y-7">
        <div className="space-y-4 border-b border-panel-border pb-6">
          <div className="flex items-center gap-3">
            <div className="grid size-11 place-items-center rounded-2xl border border-gold/30 bg-gold-soft text-gold shadow-elegant">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div className="min-w-0">
              <p className="font-display text-lg font-bold leading-tight text-ivory">SchoolSmartEYE</p>
              <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-gold/80">School Intelligence</p>
            </div>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-mist/45">Workspace</p>
            <h1 className="mt-1 truncate font-display text-xl font-bold leading-tight text-ivory">{schoolName}</h1>
            <p className="mt-2 text-xs leading-relaxed text-mist/60">Unified safety, academic and operational intelligence.</p>
          </div>
          <div className="flex items-center gap-2 rounded-xl border border-panel-border bg-white/[0.035] px-3 py-2 text-xs">
            <span className={`h-2 w-2 rounded-full ${statusTone} ${status === "connected" ? "shadow-[0_0_10px_rgba(120,182,154,.65)]" : ""}`} />
            <span className="text-mist/70">Edge connection</span>
            <span className="ml-auto font-semibold text-ivory">{statusLabel}</span>
          </div>
        </div>

        <nav aria-label="Main navigation" className="space-y-5">
          {groups.map((group) => (
            <section key={group} className="space-y-2">
              <p className="px-3 text-[10px] font-bold uppercase tracking-[0.2em] text-gold/70">{group}</p>
              <div className="space-y-1">
                {visibleNavigation.filter((item) => item.group === group).map((item) => {
                  const Icon = item.icon;
                  const isActive = activePage === item.page;
                  return (
                    <button
                      key={item.page}
                      type="button"
                      aria-current={isActive ? "page" : undefined}
                      onClick={() => onNavigate(item.page)}
                      className={`group flex w-full items-center gap-3 rounded-xl border px-3 py-2.5 text-left text-sm transition-all duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-gold ${
                        isActive
                          ? "border-gold/30 bg-gold-soft font-semibold text-ivory shadow-[inset_3px_0_0_#c5a66a]"
                          : "border-transparent text-mist/65 hover:border-white/10 hover:bg-white/[0.045] hover:text-ivory"
                      }`}
                    >
                      <Icon className={`h-4 w-4 shrink-0 ${isActive ? "text-gold" : "text-mist/45 group-hover:text-gold"}`} />
                      <span>{item.label}</span>
                      {isActive && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-gold" />}
                    </button>
                  );
                })}
              </div>
            </section>
          ))}
        </nav>
      </div>

      <div className="mt-8 space-y-3 border-t border-panel-border pt-5">
        {user && (
          <div className="flex items-center justify-between gap-3 rounded-xl border border-panel-border bg-white/[0.035] p-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-ivory">{user.full_name || user.username}</p>
              <p className="text-[11px] capitalize text-mist/55">{user.role}</p>
            </div>
            <button type="button" onClick={logout} title="Sign out" aria-label="Sign out" className="rounded-lg border border-panel-border p-2 text-mist/65 transition hover:border-gold/40 hover:bg-gold-soft hover:text-gold">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        )}
        <div className="rounded-xl border border-gold/15 bg-gold-soft/40 p-3">
          <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-gold">Privacy by design</p>
          <p className="mt-1.5 text-[11px] leading-relaxed text-mist/60">Tenant-scoped access, human oversight and verified data provenance.</p>
        </div>
      </div>
    </aside>
  );
}
