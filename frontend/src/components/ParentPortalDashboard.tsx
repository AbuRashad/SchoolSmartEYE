import { useEffect, useState } from "react";
import { Bell, CalendarDays, LogOut, ShieldCheck, UserRound } from "lucide-react";
import { useAuth } from "../AuthContext";
import { authFetch } from "../auth";
import type { ParentStudent, ParentStudentSummary } from "../types";

export function ParentPortalDashboard() {
  const { user, logout } = useAuth();
  const [students, setStudents] = useState<ParentStudent[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [summary, setSummary] = useState<ParentStudentSummary | null>(null);
  const [loadingStudents, setLoadingStudents] = useState(true);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function loadStudents() {
      setLoadingStudents(true);
      setError(null);
      try {
        const response = await authFetch("/api/v1/parent/students");
        if (!response.ok) throw new Error(response.status === 403 ? "Parent access is required." : `Unable to load linked students (HTTP ${response.status}).`);
        const data = (await response.json()) as ParentStudent[];
        if (!active) return;
        setStudents(data);
        setSelectedId(data[0]?.student_id ?? "");
      } catch (err) {
        if (active) setError((err as Error).message);
      } finally {
        if (active) setLoadingStudents(false);
      }
    }
    void loadStudents();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setSummary(null);
      return;
    }
    let active = true;
    async function loadSummary() {
      setLoadingSummary(true);
      setError(null);
      setSummary(null);
      try {
        const response = await authFetch(`/api/v1/parent/students/${encodeURIComponent(selectedId)}/summary`);
        if (!response.ok) throw new Error(response.status === 404 ? "This student is not linked to your parent account." : `Unable to load student summary (HTTP ${response.status}).`);
        const data = (await response.json()) as ParentStudentSummary;
        if (active) setSummary(data);
      } catch (err) {
        if (active) setError((err as Error).message);
      } finally {
        if (active) setLoadingSummary(false);
      }
    }
    void loadSummary();
    return () => { active = false; };
  }, [selectedId]);

  return (
    <div className="min-h-screen bg-academic px-4 py-5 text-white lg:px-8">
      <div className="mx-auto max-w-5xl space-y-6">
        <header className="flex flex-wrap items-center justify-between gap-4 rounded-[2rem] border border-white/10 bg-panel px-6 py-5 shadow-panel">
          <div className="flex items-center gap-3">
            <div className="rounded-2xl bg-cobalt/20 p-3 text-sky"><ShieldCheck className="h-6 w-6" /></div>
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-mist/55">SchoolSmartEYE</p>
              <h1 className="text-2xl font-semibold">Parent Portal</h1>
              <p className="mt-1 text-sm text-mist/65">Verified student information and school updates</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-sm font-medium">{user?.full_name || user?.username}</p>
              <p className="text-xs capitalize text-mist/55">{user?.role}</p>
            </div>
            <button type="button" onClick={logout} className="rounded-xl border border-white/10 p-2 text-mist/75 hover:bg-white/10" aria-label="Sign out">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </header>

        <section className="rounded-[2rem] border border-white/10 bg-panel/80 p-6 shadow-panel">
          <div className="flex items-center gap-2 text-sm font-medium text-mist/75"><UserRound className="h-4 w-4" /> Linked students</div>
          {loadingStudents ? (
            <p className="mt-4 text-sm text-mist/60">Loading verified student links…</p>
          ) : students.length === 0 ? (
            <div className="mt-4 rounded-2xl border border-white/10 bg-white/5 p-5 text-sm text-mist/70">
              No verified student link is currently associated with this account. Please contact the school administration.
            </div>
          ) : (
            <div className="mt-4 flex flex-wrap gap-2">
              {students.map((student) => (
                <button
                  key={student.student_id}
                  type="button"
                  onClick={() => setSelectedId(student.student_id)}
                  className={`rounded-xl border px-4 py-3 text-left transition ${selectedId === student.student_id ? "border-cobalt bg-cobalt/20 text-white" : "border-white/10 bg-white/5 text-mist/75 hover:bg-white/10"}`}
                >
                  <span className="block text-sm font-semibold">{student.name}</span>
                  <span className="mt-1 block text-xs text-mist/55">{student.grade} · {student.class_section}</span>
                </button>
              ))}
            </div>
          )}
        </section>

        {error && <div role="alert" className="rounded-2xl border border-critical/40 bg-critical/10 px-5 py-4 text-sm text-critical">{error}</div>}

        {loadingSummary && <div className="rounded-2xl border border-white/10 bg-panel p-6 text-sm text-mist/60">Loading student summary…</div>}

        {summary && !loadingSummary && (
          <>
            <section className="rounded-[2rem] border border-white/10 bg-panel/80 p-6 shadow-panel">
              <div className="flex items-center gap-2"><CalendarDays className="h-5 w-5 text-sky" /><h2 className="text-lg font-semibold">Attendance — last 7 days</h2></div>
              <p className="mt-1 text-sm text-mist/55">{summary.student.name} · {summary.student.grade} · {summary.student.class_section}</p>
              {summary.attendance.length === 0 ? (
                <p className="mt-5 text-sm text-mist/60">No attendance records are available for this period.</p>
              ) : (
                <div className="mt-5 divide-y divide-white/8">
                  {summary.attendance.map((item) => (
                    <div key={item.date} className="flex flex-wrap items-center justify-between gap-3 py-3">
                      <span className="text-sm text-mist/80">{new Date(`${item.date}T00:00:00`).toLocaleDateString()}</span>
                      <span className={`rounded-full px-3 py-1 text-xs font-medium capitalize ${item.status === "present" ? "bg-safe/15 text-safe" : item.status === "absent" ? "bg-critical/15 text-critical" : "bg-warning/15 text-warning"}`}>{item.status}</span>
                      <span className="text-xs text-mist/55">{item.arrival_time ? new Date(item.arrival_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"}</span>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="rounded-[2rem] border border-white/10 bg-panel/80 p-6 shadow-panel">
              <div className="flex items-center gap-2"><Bell className="h-5 w-5 text-sky" /><h2 className="text-lg font-semibold">School notifications</h2></div>
              {summary.notifications.length === 0 ? (
                <p className="mt-5 text-sm text-mist/60">No notifications are available.</p>
              ) : (
                <div className="mt-4 space-y-3">
                  {summary.notifications.map((item) => (
                    <article key={item.notification_id} className="rounded-2xl border border-white/8 bg-white/5 p-4">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-xs uppercase tracking-wider text-sky">{item.notification_type}</span>
                        <span className="text-xs text-mist/50">{new Date(item.sent_at).toLocaleString()}</span>
                      </div>
                      <p className="mt-2 text-sm text-mist/85">{item.message}</p>
                    </article>
                  ))}
                </div>
              )}
            </section>
          </>
        )}

        <p className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4 text-xs leading-relaxed text-mist/55">
          Privacy notice: {summary?.data_notice ?? "Only information connected to an active, school-verified parent link is shown. Live location and camera feeds are not available in this portal."}
        </p>
      </div>
    </div>
  );
}
