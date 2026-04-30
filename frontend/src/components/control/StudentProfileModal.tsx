import { useCallback, useEffect, useState } from "react";
import {
  X, User, Calendar, Watch, Bell, Edit3, MapPin, Clock, TrendingUp,
  Shield, ShieldAlert, ShieldCheck, AlertTriangle, CheckCircle2, XCircle,
  Battery, BatteryLow, RefreshCw, Trash2, Save, Users, Activity, Info, Brain,
} from "lucide-react";
import type { AttendanceDay, StudentProfile, StudentUpdatePayload, EngagementSnapshotRecord } from "../../types";
import { api } from "./api";
import { Field, inputCls, type Flash } from "./ui";
import { useStudentBehavioralHistory } from "../../hooks/useSSIData";

type Tab = "overview" | "attendance" | "bracelet" | "notifications" | "engagement" | "edit";

const TABS: { id: Tab; label: string; icon: typeof User }[] = [
  { id: "overview", label: "Overview", icon: User },
  { id: "attendance", label: "Attendance", icon: Calendar },
  { id: "bracelet", label: "Bracelet", icon: Watch },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "engagement", label: "Engagement", icon: Brain },
  { id: "edit", label: "Edit", icon: Edit3 },
];

const fmtTime = (iso: string | null) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }); }
  catch { return iso; }
};
const fmtDate = (iso: string | null) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleDateString([], { month: "short", day: "numeric" }); }
  catch { return iso; }
};
const fmtFull = (iso: string | null) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString([], {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
    });
  } catch { return iso; }
};
const wkShort = (d: string) => {
  try { return new Date(d + "T00:00:00Z").toLocaleDateString([], { weekday: "short" }); }
  catch { return d; }
};

// ── Small UI ─────────────────────────────────────────────────────────────────

function SafetyBadge({ status }: { status: StudentProfile["safety_status"] }) {
  const cfg = {
    safe: { I: ShieldCheck, c: "border-safe/40 bg-safe/10 text-safe", l: "Safe" },
    warning: { I: ShieldAlert, c: "border-amber-400/40 bg-amber-400/10 text-amber-300", l: "Warning" },
    critical: { I: ShieldAlert, c: "border-critical/40 bg-critical/10 text-critical", l: "Critical" },
    unknown: { I: Shield, c: "border-white/10 bg-white/5 text-mist/70", l: "Unknown" },
  }[status];
  const { I, c, l } = cfg;
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider ${c}`}>
      <I className="h-3.5 w-3.5" /> {l}
    </span>
  );
}

function AttendancePill({ status }: { status: AttendanceDay["status"] }) {
  const cfg = {
    present: { I: CheckCircle2, c: "border-safe/40 bg-safe/10 text-safe", l: "Present" },
    late: { I: Clock, c: "border-amber-400/40 bg-amber-400/10 text-amber-300", l: "Late" },
    absent: { I: XCircle, c: "border-critical/40 bg-critical/10 text-critical", l: "Absent" },
    unknown: { I: AlertTriangle, c: "border-white/10 bg-white/5 text-mist/70", l: "—" },
  }[status];
  const { I, c, l } = cfg;
  return (
    <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium ${c}`}>
      <I className="h-3 w-3" /> {l}
    </span>
  );
}

function StatCard({
  icon: Icon, label, value, sublabel, tone = "default",
}: {
  icon: typeof User; label: string; value: string | number; sublabel?: string;
  tone?: "default" | "good" | "warn" | "bad";
}) {
  const c = {
    default: "border-white/10 bg-white/5 text-white",
    good: "border-safe/30 bg-safe/10 text-safe",
    warn: "border-amber-400/30 bg-amber-400/10 text-amber-200",
    bad: "border-critical/30 bg-critical/10 text-critical",
  }[tone];
  return (
    <div className={`rounded-2xl border px-4 py-3 ${c}`}>
      <div className="flex items-center justify-between">
        <span className="text-[11px] uppercase tracking-wider opacity-80">{label}</span>
        <Icon className="h-4 w-4 opacity-80" />
      </div>
      <div className="mt-2 text-xl font-semibold">{value}</div>
      {sublabel && <div className="mt-0.5 text-[11px] opacity-70">{sublabel}</div>}
    </div>
  );
}

function BatteryBar({ level, low }: { level: number; low: boolean }) {
  const color = low ? "bg-critical" : level < 40 ? "bg-amber-400" : "bg-safe";
  return (
    <div className="w-full">
      <div className="h-2 overflow-hidden rounded-full bg-white/10">
        <div className={`h-full ${color} transition-all`} style={{ width: `${level}%` }} />
      </div>
      <div className="mt-1 flex items-center gap-1 text-[11px] text-mist/70">
        {low ? <BatteryLow className="h-3.5 w-3.5 text-critical" /> : <Battery className="h-3.5 w-3.5" />}
        {level}% {low && <span className="text-critical">· low</span>}
      </div>
    </div>
  );
}

function WeeklyStrip({ days }: { days: AttendanceDay[] }) {
  return (
    <div className="grid grid-cols-7 gap-2">
      {days.map((d) => {
        const c = {
          present: "border-safe/50 bg-safe/15 text-safe",
          late: "border-amber-400/50 bg-amber-400/15 text-amber-200",
          absent: "border-critical/50 bg-critical/15 text-critical",
          unknown: "border-white/10 bg-white/5 text-mist/60",
        }[d.status];
        return (
          <div key={d.date}
            className={`flex flex-col items-center justify-center rounded-xl border px-2 py-3 text-[11px] ${c}`}
            title={`${d.date} — ${d.status}`}>
            <div className="font-semibold">{wkShort(d.date)}</div>
            <div className="mt-0.5 opacity-80">{fmtDate(d.date)}</div>
            <div className="mt-1.5 text-[10px] uppercase tracking-wider opacity-80">
              {d.status === "unknown" ? "—" : d.status.charAt(0)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Tabs ─────────────────────────────────────────────────────────────────────

function OverviewTab({ profile }: { profile: StudentProfile }) {
  const todayTone = profile.today_status === "present" ? "good"
    : profile.today_status === "late" ? "warn"
    : profile.today_status === "absent" ? "bad" : "default";
  const monthTone = profile.monthly_attendance_pct >= 90 ? "good"
    : profile.monthly_attendance_pct >= 75 ? "warn" : "bad";

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard icon={CheckCircle2} label="Today"
          value={profile.today_status === "unknown" ? "—"
            : profile.today_status.charAt(0).toUpperCase() + profile.today_status.slice(1)}
          sublabel={profile.arrival_time ? `Arrived ${fmtTime(profile.arrival_time)}` : "No record"}
          tone={todayTone} />
        <StatCard icon={TrendingUp} label="Streak" value={`${profile.attendance_streak}d`}
          sublabel="Consecutive days"
          tone={profile.attendance_streak >= 5 ? "good" : "default"} />
        <StatCard icon={Calendar} label="Monthly"
          value={`${profile.monthly_attendance_pct}%`}
          sublabel={`${profile.last_30_days_present}/${profile.last_30_days_total} days`}
          tone={monthTone} />
        <StatCard icon={Bell} label="Unread Alerts"
          value={profile.unread_notifications}
          sublabel={`${profile.notifications.length} total`}
          tone={profile.unread_notifications > 0 ? "warn" : "default"} />
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-panel/60 p-4">
          <h4 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-mist/60">
            <MapPin className="h-3.5 w-3.5" /> Current Location
          </h4>
          {profile.last_seen_zone_label ? (
            <>
              <div className="text-lg font-semibold text-white">{profile.last_seen_zone_label}</div>
              <div className="mt-1 font-mono text-[11px] text-mist/60">{profile.last_seen_zone}</div>
              {profile.open_incidents_in_last_zone > 0 && (
                <div className="mt-3 flex items-center gap-2 rounded-xl border border-amber-400/40 bg-amber-400/10 px-3 py-2 text-xs text-amber-200">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  {profile.open_incidents_in_last_zone} open incident
                  {profile.open_incidents_in_last_zone !== 1 ? "s" : ""} in this zone
                </div>
              )}
            </>
          ) : <div className="text-sm text-mist/60">No recent location data.</div>}
        </div>

        <div className="rounded-2xl border border-white/10 bg-panel/60 p-4">
          <h4 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-mist/60">
            <Users className="h-3.5 w-3.5" /> Parent / Guardian
          </h4>
          <div className="font-mono text-sm text-white">{profile.parent_id}</div>
          <div className="mt-3 grid grid-cols-2 gap-2 text-[12px] text-mist/70">
            <div>
              <div className="text-[10px] uppercase tracking-wider text-mist/50">Arrival</div>
              <div className="text-white">{fmtTime(profile.arrival_time)}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-mist/50">Departure</div>
              <div className="text-white">{fmtTime(profile.departure_time)}</div>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-panel/60 p-4">
        <h4 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-mist/60">
          <Watch className="h-3.5 w-3.5" /> Assigned Bracelet
        </h4>
        {profile.bracelet ? (
          <div className="grid gap-4 md:grid-cols-[1fr_200px] md:items-center">
            <div>
              <div className="font-mono text-sm text-white">{profile.bracelet.bracelet_id}</div>
              <div className="mt-1 font-mono text-[11px] text-mist/60">{profile.bracelet.mac_address}</div>
              <div className="mt-2 text-[12px] text-mist/70">
                Last seen <span className="text-white">{profile.bracelet.last_seen_zone_label || "—"}</span>
                {profile.bracelet.last_seen_at && <> · {fmtFull(profile.bracelet.last_seen_at)}</>}
              </div>
            </div>
            <BatteryBar level={profile.bracelet.battery_level} low={profile.bracelet.low_battery} />
          </div>
        ) : <div className="text-sm text-mist/60">No bracelet assigned to this student.</div>}
      </div>

      <div className="rounded-2xl border border-white/10 bg-panel/60 p-4">
        <h4 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-mist/60">
          <Activity className="h-3.5 w-3.5" /> Last 7 Days
        </h4>
        <WeeklyStrip days={profile.weekly_attendance} />
      </div>
    </div>
  );
}

function AttendanceTab({ profile }: { profile: StudentProfile }) {
  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-white/10 bg-panel/60 p-4">
        <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-mist/60">Last 7 Days</h4>
        <WeeklyStrip days={profile.weekly_attendance} />
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <StatCard icon={TrendingUp} label="Streak" value={`${profile.attendance_streak} days`}
          tone={profile.attendance_streak >= 5 ? "good" : "default"} />
        <StatCard icon={Calendar} label="Monthly %" value={`${profile.monthly_attendance_pct}%`}
          sublabel={`${profile.last_30_days_present} present`}
          tone={profile.monthly_attendance_pct >= 90 ? "good" : profile.monthly_attendance_pct >= 75 ? "warn" : "bad"} />
        <StatCard icon={Activity} label="Days Recorded" value={profile.last_30_days_total} sublabel="of 30" />
      </div>
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-panel/60">
        <div className="border-b border-white/10 bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-wider text-mist/60">
          30-Day History
        </div>
        <table className="w-full text-sm">
          <thead className="text-left text-[11px] uppercase tracking-wider text-mist/50">
            <tr>
              <th className="px-4 py-2">Date</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Arrival</th>
              <th className="px-4 py-2">Departure</th>
              <th className="px-4 py-2">Last Zone</th>
            </tr>
          </thead>
          <tbody>
            {profile.recent_attendance.map((d) => (
              <tr key={d.date} className="border-t border-white/5">
                <td className="px-4 py-2 font-mono text-[12px] text-mist/80">
                  {d.date} <span className="text-mist/50">· {wkShort(d.date)}</span>
                </td>
                <td className="px-4 py-2"><AttendancePill status={d.status} /></td>
                <td className="px-4 py-2 text-mist/75">{fmtTime(d.arrival_time)}</td>
                <td className="px-4 py-2 text-mist/75">{fmtTime(d.departure_time)}</td>
                <td className="px-4 py-2 text-mist/75">{d.last_seen_zone_label || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function BraceletTab({ profile }: { profile: StudentProfile }) {
  if (!profile.bracelet) {
    return (
      <div className="rounded-2xl border border-white/10 bg-panel/60 px-4 py-8 text-center">
        <Watch className="mx-auto mb-2 h-10 w-10 text-mist/40" />
        <div className="text-sm text-mist/70">No bracelet assigned to this student.</div>
        <div className="mt-1 text-[12px] text-mist/50">Use the Bracelets tab to register and assign one.</div>
      </div>
    );
  }
  const b = profile.bracelet;
  return (
    <div className="rounded-2xl border border-white/10 bg-panel/60 p-5">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-cobalt/40 bg-cobalt/10 text-cobalt">
          <Watch className="h-6 w-6" />
        </div>
        <div className="flex-1">
          <div className="font-mono text-lg font-semibold text-white">{b.bracelet_id}</div>
          <div className="font-mono text-[11px] text-mist/60">{b.mac_address}</div>
        </div>
        <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${
          b.is_active ? "border-safe/40 bg-safe/10 text-safe" : "border-white/15 bg-white/5 text-mist/70"
        }`}>{b.is_active ? "Active" : "Inactive"}</span>
      </div>
      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <div>
          <div className="mb-2 text-[11px] uppercase tracking-wider text-mist/50">Battery</div>
          <BatteryBar level={b.battery_level} low={b.low_battery} />
        </div>
        <div>
          <div className="mb-1 text-[11px] uppercase tracking-wider text-mist/50">Firmware</div>
          <div className="font-mono text-sm text-white">{b.firmware_version}</div>
        </div>
      </div>
      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-white/10 bg-black/20 p-3">
          <div className="mb-1 flex items-center gap-2 text-[11px] uppercase tracking-wider text-mist/50">
            <MapPin className="h-3 w-3" /> Last Seen Zone
          </div>
          <div className="text-sm text-white">{b.last_seen_zone_label || "—"}</div>
          {b.last_seen_zone && <div className="mt-0.5 font-mono text-[11px] text-mist/60">{b.last_seen_zone}</div>}
        </div>
        <div className="rounded-xl border border-white/10 bg-black/20 p-3">
          <div className="mb-1 flex items-center gap-2 text-[11px] uppercase tracking-wider text-mist/50">
            <Clock className="h-3 w-3" /> Last Heartbeat
          </div>
          <div className="text-sm text-white">{fmtFull(b.last_seen_at)}</div>
        </div>
      </div>
      {b.notes && (
        <div className="mt-5 rounded-xl border border-white/10 bg-black/20 p-3">
          <div className="mb-1 flex items-center gap-2 text-[11px] uppercase tracking-wider text-mist/50">
            <Info className="h-3 w-3" /> Notes
          </div>
          <div className="text-sm text-mist/80">{b.notes}</div>
        </div>
      )}
    </div>
  );
}

// ── Engagement helpers ────────────────────────────────────────────────────────

const ENGAGEMENT_STATE_CFG = {
  engaged:    { color: "text-safe",    bg: "bg-safe/10",    border: "border-safe/40",    label: "Engaged" },
  attentive:  { color: "text-sky",     bg: "bg-sky/10",     border: "border-sky/40",     label: "Attentive" },
  distracted: { color: "text-warning", bg: "bg-warning/10", border: "border-warning/40", label: "Distracted" },
  drowsy:     { color: "text-critical",bg: "bg-critical/10",border: "border-critical/40",label: "Drowsy" },
  unknown:    { color: "text-mist/60", bg: "bg-white/5",    border: "border-white/10",   label: "Unknown" },
} as const;

const TREND_CFG = {
  improving: { color: "text-safe",    label: "↑ Improving" },
  stable:    { color: "text-sky",     label: "→ Stable" },
  declining: { color: "text-critical",label: "↓ Declining" },
} as const;

function EngagementStateBadge({ state }: { state: EngagementSnapshotRecord["state"] }) {
  const cfg = ENGAGEMENT_STATE_CFG[state] ?? ENGAGEMENT_STATE_CFG.unknown;
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-medium ${cfg.border} ${cfg.bg} ${cfg.color}`}>
      {cfg.label}
    </span>
  );
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 70 ? "bg-safe" : pct >= 40 ? "bg-amber-400" : "bg-critical";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
        <div className={`h-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 shrink-0 text-right text-[11px] text-mist/70">{pct}%</span>
    </div>
  );
}

function EngagementTab({ studentId, profile }: { studentId: string; profile: StudentProfile }) {
  const { data: history, loading, error } = useStudentBehavioralHistory(studentId, 30);
  const summary = profile.engagement_summary;

  return (
    <div className="space-y-5">
      {/* Summary cards */}
      {summary ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <StatCard
            icon={Brain}
            label="Avg Score (7d)"
            value={`${Math.round(summary.avg_score_7d * 100)}%`}
            tone={summary.avg_score_7d >= 0.7 ? "good" : summary.avg_score_7d >= 0.4 ? "warn" : "bad"}
          />
          <StatCard
            icon={Activity}
            label="Dominant State"
            value={ENGAGEMENT_STATE_CFG[summary.dominant_state]?.label ?? summary.dominant_state}
            tone={summary.dominant_state === "engaged" || summary.dominant_state === "attentive" ? "good"
              : summary.dominant_state === "distracted" || summary.dominant_state === "drowsy" ? "bad" : "default"}
          />
          <StatCard
            icon={TrendingUp}
            label="Trend"
            value={TREND_CFG[summary.trend as keyof typeof TREND_CFG]?.label ?? summary.trend}
            sublabel={`${summary.total_snapshots_7d} snapshots`}
            tone={summary.trend === "improving" ? "good" : summary.trend === "declining" ? "bad" : "default"}
          />
          <StatCard
            icon={AlertTriangle}
            label="A/V Mismatches"
            value={summary.mismatch_count_7d}
            sublabel="Last 7 days"
            tone={summary.mismatch_count_7d > 0 ? "warn" : "default"}
          />
        </div>
      ) : (
        <div className="rounded-2xl border border-white/10 bg-panel/60 px-4 py-6 text-center text-sm text-mist/60">
          <Brain className="mx-auto mb-2 h-8 w-8 text-mist/40" />
          No engagement data recorded yet for this student.
        </div>
      )}

      {/* Timeline */}
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-panel/60">
        <div className="flex items-center justify-between border-b border-white/10 bg-white/5 px-4 py-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-mist/60">
            Engagement Timeline (last 30 days)
          </span>
          {loading && <RefreshCw className="h-3.5 w-3.5 animate-spin text-mist/50" />}
        </div>

        {error ? (
          <div className="px-4 py-6 text-center text-sm text-critical/80">{error}</div>
        ) : history.length === 0 && !loading ? (
          <div className="px-4 py-6 text-center text-sm text-mist/60">No snapshots in the last 30 days.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-[11px] uppercase tracking-wider text-mist/50">
                <tr>
                  <th className="px-4 py-2">Time</th>
                  <th className="px-4 py-2">Session</th>
                  <th className="px-4 py-2">State</th>
                  <th className="px-4 py-2 w-36">Score</th>
                  <th className="px-4 py-2">Audio</th>
                  <th className="px-4 py-2">Zone</th>
                </tr>
              </thead>
              <tbody>
                {history.map((s) => (
                  <tr
                    key={`${s.student_id}-${s.recorded_at}`}
                    className={`border-t border-white/5 ${s.audio_visual_mismatch ? "bg-amber-400/5" : ""}`}
                  >
                    <td className="px-4 py-2 font-mono text-[11px] text-mist/70">
                      {(() => { try { return new Date(s.recorded_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }); } catch { return s.recorded_at; } })()}
                    </td>
                    <td className="px-4 py-2 font-mono text-[11px] text-mist/60">{s.session_id}</td>
                    <td className="px-4 py-2"><EngagementStateBadge state={s.state} /></td>
                    <td className="px-4 py-2 w-36"><ScoreBar score={s.score} /></td>
                    <td className="px-4 py-2">
                      {s.audio_context ? (
                        <span className={`text-[11px] ${s.audio_visual_mismatch ? "text-amber-300 font-semibold" : "text-mist/70"}`}>
                          {s.audio_context}
                          {s.audio_visual_mismatch && " ⚠"}
                        </span>
                      ) : <span className="text-mist/40">—</span>}
                    </td>
                    <td className="px-4 py-2 font-mono text-[11px] text-mist/60">{s.zone_id ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

function NotificationsTab({ profile }: { profile: StudentProfile }) {
  if (profile.notifications.length === 0) {
    return (
      <div className="rounded-2xl border border-white/10 bg-panel/60 px-4 py-8 text-center">
        <Bell className="mx-auto mb-2 h-10 w-10 text-mist/40" />
        <div className="text-sm text-mist/70">No notifications yet.</div>
      </div>
    );
  }
  return (
    <div className="space-y-2">
      {profile.notifications.map((n) => {
        const typeCls =
          n.notification_type === "attendance" ? "border-cobalt/40 bg-cobalt/10 text-cobalt"
          : n.notification_type === "safety" ? "border-amber-400/40 bg-amber-400/10 text-amber-300"
          : "border-white/15 bg-white/5 text-mist/80";
        return (
          <div key={n.notification_id}
            className={`flex items-start gap-3 rounded-2xl border px-4 py-3 ${
              n.read ? "border-white/10 bg-panel/40" : "border-cobalt/30 bg-cobalt/5"
            }`}>
            <span className={`rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${typeCls}`}>
              {n.notification_type}
            </span>
            <div className="flex-1 min-w-0">
              <div className={`text-sm ${n.read ? "text-mist/80" : "text-white"}`}>{n.message}</div>
              <div className="mt-0.5 text-[11px] text-mist/50">{fmtFull(n.sent_at)}</div>
            </div>
            {!n.read && <span className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full bg-cobalt" />}
          </div>
        );
      })}
    </div>
  );
}

function EditTab({
  form, setForm, onSubmit, onDelete, busy,
}: {
  form: StudentUpdatePayload;
  setForm: (f: StudentUpdatePayload) => void;
  onSubmit: (e: React.FormEvent) => void;
  onDelete: () => void;
  busy: boolean;
}) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="rounded-2xl border border-white/10 bg-panel/60 p-5 space-y-3">
        <h4 className="text-sm font-semibold text-white">Edit Profile</h4>
        <Field label="Full Name">
          <input value={form.name ?? ""} onChange={(e) => setForm({ ...form, name: e.target.value })}
            className={inputCls} required />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Grade">
            <input value={form.grade ?? ""} onChange={(e) => setForm({ ...form, grade: e.target.value })}
              className={inputCls} required />
          </Field>
          <Field label="Section">
            <input value={form.class_section ?? ""} onChange={(e) => setForm({ ...form, class_section: e.target.value })}
              className={inputCls} required />
          </Field>
        </div>
        <Field label="Parent ID">
          <input value={form.parent_id ?? ""} onChange={(e) => setForm({ ...form, parent_id: e.target.value.trim() })}
            className={inputCls} required />
        </Field>
        <Field label="Photo Initial" hint="Single uppercase letter">
          <input value={form.photo_initial ?? ""}
            onChange={(e) => setForm({ ...form, photo_initial: e.target.value.slice(0, 1).toUpperCase() })}
            className={inputCls} maxLength={1} />
        </Field>
        <label className="flex items-center gap-2 text-sm text-mist/80">
          <input type="checkbox" checked={form.is_active ?? true}
            onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            className="h-4 w-4 rounded border-white/20 bg-black/30" />
          Active
        </label>
      </div>

      <div className="flex flex-wrap justify-between gap-2">
        <button type="button" onClick={onDelete} disabled={busy}
          className="flex items-center gap-2 rounded-xl border border-critical/40 bg-critical/10 px-4 py-2 text-sm text-critical hover:bg-critical/20 disabled:opacity-50">
          <Trash2 className="h-4 w-4" /> Delete Student
        </button>
        <button type="submit" disabled={busy}
          className="flex items-center gap-2 rounded-xl bg-cobalt px-4 py-2 text-sm font-semibold text-white transition hover:bg-cobalt/90 disabled:opacity-50">
          <Save className="h-4 w-4" /> Save Changes
        </button>
      </div>
    </form>
  );
}

// ── Header + TabBar ─────────────────────────────────────────────────────────

function ProfileHeader({
  profile, onToggleActive, busy,
}: { profile: StudentProfile; onToggleActive: () => void; busy: boolean }) {
  const initial = profile.photo_initial || profile.name.charAt(0).toUpperCase();
  return (
    <div className="border-b border-white/10 bg-gradient-to-r from-cobalt/10 via-transparent to-transparent px-6 py-5">
      <div className="flex flex-wrap items-start gap-4">
        <div className="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-2xl border border-cobalt/40 bg-cobalt/15 text-2xl font-bold text-white">
          {initial}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="truncate text-xl font-semibold text-white">{profile.name}</h2>
            <SafetyBadge status={profile.safety_status} />
            <span className={`rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${
              profile.is_active ? "border-safe/40 bg-safe/10 text-safe" : "border-white/15 bg-white/5 text-mist/70"
            }`}>{profile.is_active ? "Active" : "Inactive"}</span>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-mist/70">
            <span className="font-mono text-[12px]">{profile.student_id}</span>
            <span>·</span><span>{profile.grade}</span>
            <span>·</span><span>Section {profile.class_section}</span>
            <span>·</span><span className="font-mono text-[12px]">Parent {profile.parent_id}</span>
          </div>
        </div>
        <button type="button" onClick={onToggleActive} disabled={busy}
          className={`rounded-xl border px-3 py-1.5 text-xs font-medium transition disabled:opacity-50 ${
            profile.is_active
              ? "border-amber-400/40 bg-amber-400/10 text-amber-200 hover:bg-amber-400/20"
              : "border-safe/40 bg-safe/10 text-safe hover:bg-safe/20"
          }`}>
          {profile.is_active ? "Deactivate" : "Activate"}
        </button>
      </div>
    </div>
  );
}

function TabBar({ tab, setTab, unread }: { tab: Tab; setTab: (t: Tab) => void; unread: number }) {
  return (
    <div className="flex flex-wrap gap-1 border-b border-white/10 px-6 pt-3">
      {TABS.map((t) => {
        const Icon = t.icon;
        const active = t.id === tab;
        return (
          <button key={t.id} type="button" onClick={() => setTab(t.id)}
            className={`relative flex items-center gap-2 rounded-t-xl px-4 py-2 text-sm transition ${
              active ? "bg-white/8 text-white" : "text-mist/70 hover:bg-white/5 hover:text-white"
            }`}>
            <Icon className="h-4 w-4" />
            {t.label}
            {t.id === "notifications" && unread > 0 && (
              <span className="ml-1 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-cobalt px-1 text-[10px] font-bold text-white">
                {unread}
              </span>
            )}
            {active && <span className="absolute inset-x-2 bottom-0 h-0.5 rounded-full bg-cobalt" />}
          </button>
        );
      })}
    </div>
  );
}

// ── Main Modal ───────────────────────────────────────────────────────────────

type Props = {
  studentId: string;
  flash: Flash;
  onClose: () => void;
  onChanged: () => void;
};

export function StudentProfileModal({ studentId, flash, onClose, onChanged }: Props) {
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<Tab>("overview");
  const [busy, setBusy] = useState(false);
  const [editForm, setEditForm] = useState<StudentUpdatePayload>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const p = await api<StudentProfile>(`/students/${encodeURIComponent(studentId)}/profile`);
      setProfile(p);
      setEditForm({
        name: p.name, grade: p.grade, class_section: p.class_section,
        parent_id: p.parent_id, photo_initial: p.photo_initial, is_active: p.is_active,
      });
    } catch (e) {
      flash("err", `Failed to load profile: ${(e as Error).message}`);
      onClose();
    } finally {
      setLoading(false);
    }
  }, [studentId, flash, onClose]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);

  const toggleActive = async () => {
    if (!profile) return;
    setBusy(true);
    try {
      await api(`/students/${encodeURIComponent(profile.student_id)}`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !profile.is_active }),
      });
      flash("ok", `Student ${!profile.is_active ? "activated" : "deactivated"}`);
      await load();
      onChanged();
    } catch (e) {
      flash("err", (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const saveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile) return;
    setBusy(true);
    try {
      await api(`/students/${encodeURIComponent(profile.student_id)}`, {
        method: "PATCH",
        body: JSON.stringify(editForm),
      });
      flash("ok", "Student updated");
      await load();
      onChanged();
      setTab("overview");
    } catch (e) {
      flash("err", (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const removeStudent = async () => {
    if (!profile) return;
    if (!confirm(`Delete student "${profile.name}"? Their bracelet (if any) will also be removed.`)) return;
    setBusy(true);
    try {
      await api(`/students/${encodeURIComponent(profile.student_id)}`, { method: "DELETE" });
      flash("ok", `Student ${profile.name} deleted`);
      onChanged();
      onClose();
    } catch (e) {
      flash("err", (e as Error).message);
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-stretch justify-center bg-black/70 p-0 backdrop-blur-sm md:items-center md:p-6"
      onClick={onClose}>
      <div className="relative flex h-full w-full max-w-5xl flex-col overflow-hidden rounded-none border border-white/10 bg-[#0b1117] shadow-panel md:h-[min(90vh,920px)] md:rounded-[2rem]"
        onClick={(e) => e.stopPropagation()}>
        <button type="button" onClick={onClose}
          className="absolute right-4 top-4 z-10 rounded-xl border border-white/10 bg-white/5 p-2 text-mist/80 transition hover:bg-white/10 hover:text-white"
          aria-label="Close">
          <X className="h-4 w-4" />
        </button>

        {loading || !profile ? (
          <div className="flex flex-1 items-center justify-center text-mist/70">
            <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> Loading profile…
          </div>
        ) : (
          <>
            <ProfileHeader profile={profile} onToggleActive={toggleActive} busy={busy} />
            <TabBar tab={tab} setTab={setTab} unread={profile.unread_notifications} />
            <div className="flex-1 overflow-y-auto px-6 py-5">
              {tab === "overview" && <OverviewTab profile={profile} />}
              {tab === "attendance" && <AttendanceTab profile={profile} />}
              {tab === "bracelet" && <BraceletTab profile={profile} />}
              {tab === "notifications" && <NotificationsTab profile={profile} />}
              {tab === "engagement" && <EngagementTab studentId={profile.student_id} profile={profile} />}
              {tab === "edit" && (
                <EditTab form={editForm} setForm={setEditForm}
                  onSubmit={saveEdit} onDelete={removeStudent} busy={busy} />
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
