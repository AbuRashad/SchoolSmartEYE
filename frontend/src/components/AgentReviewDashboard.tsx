import { useCallback, useEffect, useMemo, useState } from "react";
import { Check, Clock3, FileText, RefreshCw, ShieldAlert, X } from "lucide-react";
import { useAuth } from "../AuthContext";
import { api } from "./control/api";

type AuditEvent = {
  event_id: string;
  event_type: string;
  actor_type: string;
  actor_user_id: number | null;
  from_status: string | null;
  to_status: string | null;
  event_metadata: Record<string, unknown>;
  created_at: string;
};

type ReviewTask = {
  action_id: string;
  school_id: string;
  source_request_id: string;
  action_kind: string;
  title: string;
  description: string;
  assigned_role: string;
  status: "pending_approval" | "open" | "rejected" | "completed" | string;
  proposed_by_user_id: number;
  approved_by_user_id: number | null;
  completed_by_user_id: number | null;
  created_at: string;
  approved_at: string | null;
  completed_at: string | null;
};

const statusStyles: Record<string, string> = {
  pending_approval: "border-amber-300/30 bg-amber-300/10 text-amber-100",
  open: "border-sky-300/30 bg-sky-300/10 text-sky-100",
  rejected: "border-rose-300/30 bg-rose-300/10 text-rose-100",
  completed: "border-emerald-300/30 bg-emerald-300/10 text-emerald-100",
};

function formatDate(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function AgentReviewDashboard() {
  const { can } = useAuth();
  const [tasks, setTasks] = useState<ReviewTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("all");
  const [expandedAuditId, setExpandedAuditId] = useState<string | null>(null);
  const [auditEvents, setAuditEvents] = useState<Record<string, AuditEvent[]>>({});
  const [auditLoadingId, setAuditLoadingId] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setError(null);
    try {
      const rows = await api<ReviewTask[]>("/agent/actions");
      setTasks(rows);
    } catch (err) {
      setError((err as Error).message || "Unable to load the review queue.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const counts = useMemo(() => ({
    pending: tasks.filter((task) => task.status === "pending_approval").length,
    open: tasks.filter((task) => task.status === "open").length,
    completed: tasks.filter((task) => task.status === "completed").length,
    rejected: tasks.filter((task) => task.status === "rejected").length,
  }), [tasks]);

  const visibleTasks = filter === "all" ? tasks : tasks.filter((task) => task.status === filter);

  async function toggleAudit(task: ReviewTask) {
    if (expandedAuditId === task.action_id) {
      setExpandedAuditId(null);
      return;
    }
    setExpandedAuditId(task.action_id);
    if (auditEvents[task.action_id]) return;
    setAuditLoadingId(task.action_id);
    try {
      const events = await api<AuditEvent[]>(
        `/agent/actions/${encodeURIComponent(task.action_id)}/audit`,
      );
      setAuditEvents((current) => ({ ...current, [task.action_id]: events }));
    } catch (err) {
      setError((err as Error).message || "Unable to load the audit history.");
    } finally {
      setAuditLoadingId(null);
    }
  }

  async function act(task: ReviewTask, action: "approve" | "reject" | "complete") {
    setBusyId(task.action_id);
    setError(null);
    try {
      await api<ReviewTask>(`/agent/actions/${encodeURIComponent(task.action_id)}/${action}`, {
        method: "POST",
      });
      await reload();
    } catch (err) {
      setError((err as Error).message || "The requested action could not be completed.");
    } finally {
      setBusyId(null);
    }
  }

  if (!can("principal")) {
    return (
      <section className="rounded-2xl border border-critical/30 bg-critical/10 p-6 text-sm text-white">
        This review queue is restricted to principals and ministry users.
      </section>
    );
  }

  return (
    <div className="space-y-5">
      <section className="rounded-[2rem] border border-white/10 bg-panel/70 px-6 py-6 shadow-panel">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-mist/50">Multi-agent governance</p>
            <h2 className="mt-2 text-2xl font-semibold text-white">Agent Review & Approval Queue</h2>
            <p className="mt-2 max-w-3xl text-sm text-mist/70">
              Review proposed follow-up tasks, approve or reject them, and record completion.
              Every item is retrieved within the authenticated school boundary.
            </p>
          </div>
          <button type="button" onClick={() => void reload()} disabled={loading}
            className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm text-mist/80 hover:bg-white/10 disabled:opacity-50">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} /> Refresh
          </button>
        </div>
      </section>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: "Awaiting approval", value: counts.pending, tone: "text-amber-200" },
          { label: "Approved / open", value: counts.open, tone: "text-sky-200" },
          { label: "Completed", value: counts.completed, tone: "text-emerald-200" },
          { label: "Rejected", value: counts.rejected, tone: "text-rose-200" },
        ].map((item) => (
          <div key={item.label} className="rounded-2xl border border-white/10 bg-panel/60 p-5">
            <p className="text-sm text-mist/60">{item.label}</p>
            <p className={`mt-2 text-3xl font-semibold ${item.tone}`}>{item.value}</p>
          </div>
        ))}
      </div>

      <section className="rounded-[2rem] border border-white/10 bg-panel/60 p-5 shadow-panel">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-white">Human oversight queue</h3>
            <p className="mt-1 text-xs text-mist/55">Actions are recorded; no external message, camera, or attendance change is executed.</p>
          </div>
          <select value={filter} onChange={(event) => setFilter(event.target.value)}
            className="rounded-xl border border-white/10 bg-slate-900 px-3 py-2 text-sm text-white">
            <option value="all">All statuses</option>
            <option value="pending_approval">Awaiting approval</option>
            <option value="open">Approved / open</option>
            <option value="completed">Completed</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>

        {error && <p role="alert" className="mt-4 rounded-xl border border-rose-300/30 bg-rose-300/10 px-4 py-3 text-sm text-rose-100">{error}</p>}
        {loading ? (
          <p className="py-12 text-center text-sm text-mist/55">Loading school review tasks…</p>
        ) : visibleTasks.length === 0 ? (
          <div className="py-12 text-center">
            <ShieldAlert className="mx-auto h-8 w-8 text-mist/35" />
            <p className="mt-3 text-sm text-mist/65">No tasks in this view.</p>
            <p className="mt-1 text-xs text-mist/40">New tasks will appear here when proposed by the agent workflow.</p>
          </div>
        ) : (
          <div className="mt-4 space-y-3">
            {visibleTasks.map((task) => (
              <article key={task.action_id} className="rounded-2xl border border-white/10 bg-slate-950/30 p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className="font-semibold text-white">{task.title}</h4>
                      <span className={`rounded-full border px-2.5 py-1 text-[11px] capitalize ${statusStyles[task.status] || "border-white/10 bg-white/5 text-mist/70"}`}>
                        {task.status.replace(/_/g, " ")}
                      </span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-mist/70">{task.description}</p>
                    <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-xs text-mist/45">
                      <span>Type: {task.action_kind.replace(/_/g, " ")}</span>
                      <span>Assigned role: {task.assigned_role}</span>
                      <span>Proposed: {formatDate(task.created_at)}</span>
                    </div>
                    <p className="mt-2 break-all text-[11px] text-mist/35">Source run: {task.source_request_id}</p>
                  </div>
                  <div className="flex shrink-0 flex-wrap gap-2">
                    {task.status === "pending_approval" && (
                      <>
                        <button type="button" disabled={busyId === task.action_id} onClick={() => void act(task, "approve")}
                          className="flex items-center gap-1.5 rounded-lg bg-emerald-500/15 px-3 py-2 text-xs font-medium text-emerald-100 hover:bg-emerald-500/25 disabled:opacity-50">
                          <Check className="h-3.5 w-3.5" /> Approve
                        </button>
                        <button type="button" disabled={busyId === task.action_id} onClick={() => void act(task, "reject")}
                          className="flex items-center gap-1.5 rounded-lg bg-rose-500/15 px-3 py-2 text-xs font-medium text-rose-100 hover:bg-rose-500/25 disabled:opacity-50">
                          <X className="h-3.5 w-3.5" /> Reject
                        </button>
                      </>
                    )}
                    {task.status === "open" && (
                      <button type="button" disabled={busyId === task.action_id} onClick={() => void act(task, "complete")}
                        className="flex items-center gap-1.5 rounded-lg bg-sky-500/15 px-3 py-2 text-xs font-medium text-sky-100 hover:bg-sky-500/25 disabled:opacity-50">
                        <Clock3 className="h-3.5 w-3.5" /> Mark completed
                      </button>
                    )}
                  </div>
                </div>
                {(task.approved_at || task.completed_at) && (
                  <div className="mt-3 border-t border-white/8 pt-3 text-xs text-mist/45">
                    {task.approved_at && <span>Approved: {formatDate(task.approved_at)} · User #{task.approved_by_user_id}</span>}
                    {task.completed_at && <span className="ml-3">Completed: {formatDate(task.completed_at)} · User #{task.completed_by_user_id}</span>}
                  </div>
                )}

                <div className="mt-3 border-t border-white/8 pt-3">
                  <button type="button" onClick={() => void toggleAudit(task)}
                    className="inline-flex items-center gap-2 text-xs font-medium text-mist/65 hover:text-white">
                    <FileText className="h-3.5 w-3.5" />
                    {expandedAuditId === task.action_id ? "Hide audit history" : "View audit history"}
                  </button>
                  {expandedAuditId === task.action_id && (
                    <div className="mt-3 rounded-xl border border-white/8 bg-black/15 p-3">
                      {auditLoadingId === task.action_id ? (
                        <p className="text-xs text-mist/50">Loading audit history…</p>
                      ) : (auditEvents[task.action_id] || []).length === 0 ? (
                        <p className="text-xs text-mist/50">No audit events are available.</p>
                      ) : (
                        <ol className="space-y-3">
                          {(auditEvents[task.action_id] || []).map((event) => (
                            <li key={event.event_id} className="flex flex-wrap items-start justify-between gap-2 text-xs">
                              <div>
                                <p className="font-medium capitalize text-white">{event.event_type.replace(/_/g, " ")}</p>
                                <p className="mt-1 text-mist/55">
                                  {event.actor_type === "agent" ? "Automated rule engine" : `Authorised user #${event.actor_user_id ?? "unknown"}`}
                                  {event.from_status && ` · ${event.from_status.replace(/_/g, " ")} → ${event.to_status?.replace(/_/g, " ")}`}
                                </p>
                                {Array.isArray(event.event_metadata.signal_codes) && event.event_metadata.signal_codes.length > 0 && (
                                  <p className="mt-1 text-mist/40">
                                    Signals: {(event.event_metadata.signal_codes as string[]).join(", ").replace(/_/g, " ")}
                                  </p>
                                )}
                              </div>
                              <time className="text-mist/40">{formatDate(event.created_at)}</time>
                            </li>
                          ))}
                        </ol>
                      )}
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
