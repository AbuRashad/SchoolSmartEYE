import { Bell, MapPin, Clock, ShieldCheck, UserCheck, Flame, Info } from "lucide-react";
import type { StudentPortalData, PortalNotification } from "../types";

type Props = { data: StudentPortalData | null };

const attendanceColors = {
  present: "border-safe/30 bg-safe/10 text-safe",
  absent: "border-critical/30 bg-critical/10 text-critical",
  late: "border-warning/30 bg-warning/10 text-warning",
};

const safetyColors = {
  safe: "border-safe/30 bg-safe/10 text-safe",
  warning: "border-warning/30 bg-warning/10 text-warning",
  unknown: "border-white/20 bg-white/5 text-mist/60",
};

const notifIcon: Record<PortalNotification["type"], typeof Bell> = {
  attendance: UserCheck,
  safety: ShieldCheck,
  info: Info,
};

const notifColor: Record<PortalNotification["type"], string> = {
  attendance: "#46c37b",
  safety: "#4f8fd8",
  info: "#9b6dff",
};

export function ParentPortalFull({ data }: Props) {
  if (!data) {
    return (
      <div className="rounded-[2rem] border border-white/10 bg-panel/70 px-6 py-12 text-center text-mist/50 shadow-panel">
        Loading student data…
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Student Header Card */}
      <section className="rounded-[2rem] border border-white/10 bg-panel/90 p-6 shadow-panel backdrop-blur">
        <div className="flex flex-wrap items-center gap-5">
          <div className="flex h-16 w-16 items-center justify-center rounded-[1.2rem] bg-cobalt/60 text-3xl font-bold text-white">
            {data.photo_initial}
          </div>
          <div>
            <h3 className="text-2xl font-bold text-white">{data.name}</h3>
            <p className="text-sm text-mist/60">{data.grade}</p>
            <p className="mt-1 font-mono text-xs text-mist/40">{data.student_id}</p>
          </div>
          <div className="ml-auto">
            <span className={`rounded-[1rem] border px-4 py-2 text-sm font-semibold uppercase ${safetyColors[data.safety_status]}`}>
              {data.safety_status === "safe" ? "✓ Safe" : data.safety_status === "warning" ? "⚠ Warning" : "? Unknown"}
            </span>
          </div>
        </div>

        {/* Status pills */}
        <div className="mt-5 grid gap-3 sm:grid-cols-2 md:grid-cols-4">
          <div className={`rounded-[1.2rem] border px-4 py-3 ${attendanceColors[data.attendance_today]}`}>
            <p className="text-[10px] uppercase tracking-[0.2em] text-white/50">Attendance</p>
            <p className="mt-1 text-base font-bold capitalize">{data.attendance_today}</p>
          </div>
          <div className="rounded-[1.2rem] border border-sky/20 bg-sky/5 px-4 py-3">
            <p className="text-[10px] uppercase tracking-[0.2em] text-mist/50 flex items-center gap-1">
              <Clock className="h-3 w-3" /> Arrival
            </p>
            <p className="mt-1 text-base font-bold text-white">{data.arrival_time}</p>
          </div>
          <div className="rounded-[1.2rem] border border-white/10 bg-white/5 px-4 py-3">
            <p className="text-[10px] uppercase tracking-[0.2em] text-mist/50 flex items-center gap-1">
              <MapPin className="h-3 w-3" /> Last Zone
            </p>
            <p className="mt-1 text-sm font-bold text-white truncate">{data.last_seen_zone}</p>
          </div>
          <div className="rounded-[1.2rem] border border-white/10 bg-white/5 px-4 py-3">
            <p className="text-[10px] uppercase tracking-[0.2em] text-mist/50">Dismissal</p>
            <p className="mt-1 text-xs font-semibold text-mist/70">{data.dismissal_status}</p>
          </div>
        </div>
      </section>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Stats + Weekly attendance */}
        <div className="space-y-4">
          <div className="grid gap-4 grid-cols-2">
            <div className="rounded-[1.6rem] border border-safe/20 bg-safe/5 px-5 py-5">
              <Flame className="h-5 w-5 text-safe" />
              <p className="mt-3 text-3xl font-bold text-white">{data.attendance_streak}</p>
              <p className="text-xs text-mist/55">Day streak</p>
            </div>
            <div className="rounded-[1.6rem] border border-sky/20 bg-sky/5 px-5 py-5">
              <UserCheck className="h-5 w-5 text-sky" />
              <p className="mt-3 text-3xl font-bold text-white">{data.monthly_attendance.toFixed(1)}%</p>
              <p className="text-xs text-mist/55">Monthly attendance</p>
            </div>
          </div>

          {/* Weekly attendance dots */}
          <section className="rounded-[1.6rem] border border-white/10 bg-panel/90 p-5 shadow-panel backdrop-blur">
            <p className="text-xs uppercase tracking-[0.24em] text-mist/50">This Week</p>
            <div className="mt-4 flex justify-between gap-2">
              {data.weekly_attendance.map((d) => (
                <div key={d.day} className="flex flex-col items-center gap-1.5">
                  <div
                    className={`h-8 w-8 rounded-full flex items-center justify-center text-[10px] font-bold transition ${
                      d.present
                        ? "bg-safe text-white"
                        : "bg-critical/20 text-critical border border-critical/30"
                    }`}
                  >
                    {d.present ? "✓" : "✗"}
                  </div>
                  <span className="text-[9px] text-mist/45">{d.day}</span>
                </div>
              ))}
            </div>
          </section>
        </div>

        {/* Notifications */}
        <section className="rounded-[2rem] border border-white/10 bg-panel/90 p-6 shadow-panel backdrop-blur">
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs uppercase tracking-[0.28em] text-mist/50">Notifications</p>
            <Bell className="h-4 w-4 text-mist/40" />
          </div>
          <div className="space-y-3">
            {data.notifications.map((n) => {
              const Icon = notifIcon[n.type];
              return (
                <div
                  key={n.id}
                  className={`flex items-start gap-3 rounded-[1.2rem] border px-4 py-3 transition ${
                    n.read ? "border-white/8 bg-white/3" : "border-sky/20 bg-sky/5"
                  }`}
                >
                  <div
                    className="mt-0.5 shrink-0 rounded-full p-1.5"
                    style={{ backgroundColor: `${notifColor[n.type]}15` }}
                  >
                    <Icon className="h-3.5 w-3.5" style={{ color: notifColor[n.type] }} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className={`text-sm ${n.read ? "text-mist/60" : "text-white font-medium"}`}>{n.message}</p>
                    <p className="mt-1 text-[10px] text-mist/35">{n.time}</p>
                  </div>
                  {!n.read && <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-sky" />}
                </div>
              );
            })}
          </div>
        </section>
      </div>

      <p className="text-center text-xs text-mist/25 pt-2">
        All data anonymized per POLICY.minor_age_threshold = 18 · Video logs expire after 72h TTL · RBAC-controlled
      </p>
    </div>
  );
}
