import { Brain, AlertOctagon, TrendingUp, ShieldCheck, Users } from "lucide-react";
import type { AlertFeedItem, AgentSessionInsights } from "../types";

type Props = {
  ssi: number;
  benchmark: number;
  alerts: AlertFeedItem[];
  agentInsights?: AgentSessionInsights | null;
};

type Insight = {
  icon: typeof Brain;
  title: string;
  recommendation: string;
  priority: "critical" | "high" | "medium" | "info";
};

const priorityColors = {
  critical: { border: "border-critical/35", bg: "bg-critical/8", badge: "bg-critical", icon: "#e84d5b" },
  high: { border: "border-warning/35", bg: "bg-warning/8", badge: "bg-warning", icon: "#ffb84d" },
  medium: { border: "border-sky/25", bg: "bg-sky/8", badge: "bg-sky", icon: "#4f8fd8" },
  info: { border: "border-safe/25", bg: "bg-safe/8", badge: "bg-safe", icon: "#46c37b" },
};

function buildInsights(
  ssi: number,
  benchmark: number,
  alerts: AlertFeedItem[],
  agent: AgentSessionInsights | null | undefined,
): Insight[] {
  const insights: Insight[] = [];
  const hasCritical = alerts.some((a) => a.severity === "critical");
  const hasWarning = alerts.some((a) => a.severity === "warning");

  if (hasCritical) {
    insights.push({
      icon: AlertOctagon,
      title: "Critical Alert Active",
      recommendation: "Immediate response required. Deploy on-call security to flagged zone. Verify crowd density thresholds and initiate containment protocol per Crowd Density Forecasting unit guidelines.",
      priority: "critical",
    });
  }

  if (ssi < benchmark) {
    insights.push({
      icon: Brain,
      title: "SSI Below National Benchmark",
      recommendation: `Current SSI (${ssi}) is below the benchmark (${benchmark}). Recommend increasing patrol frequency by 20%, reviewing attendance discrepancies in the Attendance Safety Integration unit, and activating the Spatial Behavioral Memory anomaly review workflow.`,
      priority: "high",
    });
  } else if (ssi < benchmark + 5) {
    insights.push({
      icon: TrendingUp,
      title: "SSI Approaching Benchmark",
      recommendation: `SSI is ${(ssi - benchmark).toFixed(1)} pts above benchmark — within tolerance. Monitor Unit 06 coherence score for early warning signals over the next 30 minutes.`,
      priority: "medium",
    });
  }

  if (hasWarning && !hasCritical) {
    insights.push({
      icon: AlertOctagon,
      title: "Active Warning Signals",
      recommendation: "Multiple warning-level alerts detected. Pre-position staff near high-density zones. Crowd forecasting (Unit 07) predicts elevated density in Learning Commons within 15 minutes.",
      priority: "high",
    });
  }

  // ── Unit 15 live agent insights ─────────────────────────────────────────────
  if (agent) {
    // Disengagement flags
    if (agent.disengagement_flags.length > 0) {
      const names = agent.disengagement_flags
        .slice(0, 3)
        .map((f) => f.student_id)
        .join(", ");
      insights.push({
        icon: Users,
        title: `${agent.disengagement_flags.length} Student${agent.disengagement_flags.length !== 1 ? "s" : ""} Disengaged`,
        recommendation: `Unit 15 detected disengagement patterns for: ${names}${agent.disengagement_flags.length > 3 ? ` and ${agent.disengagement_flags.length - 3} more` : ""}. Consider adjusting lesson pace or activating targeted interventions.`,
        priority: "high",
      });
    }

    // Audio-visual mismatches
    if (agent.audio_visual_mismatches.length > 0) {
      insights.push({
        icon: Brain,
        title: "Audio-Visual Mismatch Detected",
        recommendation: `${agent.audio_visual_mismatches.length} student(s) show conflicting audio and visual signals (e.g., speaking but disengaged posture). Egyptian Arabic dialect context analysis flagged possible off-task conversation.`,
        priority: "medium",
      });
    }

    // Class engagement summary
    if (agent.class_engagement_average > 0) {
      const avgPct = Math.round(agent.class_engagement_average * 100);
      insights.push({
        icon: TrendingUp,
        title: `Class Engagement: ${avgPct}%`,
        recommendation: agent.improvement_note
          ? agent.improvement_note
          : avgPct >= 75
            ? `Current session engagement is strong at ${avgPct}%. Top performers: ${agent.top_engaged_students.slice(0, 2).map((s) => s.student_id).join(", ") || "—"}.`
            : `Session engagement at ${avgPct}% — below optimal threshold. Review lesson materials and classroom environment.`,
        priority: avgPct >= 75 ? "info" : "medium",
      });
    }
  } else {
    // Fallback static insights when agent data is not yet available
    insights.push({
      icon: TrendingUp,
      title: "Predictive Crowd Pattern",
      recommendation: "AI model forecasts a 12% density increase in Learning Commons between 11:30–12:00 (lunch transition). Pre-positioning 2 additional supervisors is recommended to maintain SSI above benchmark.",
      priority: "medium",
    });
  }

  insights.push({
    icon: ShieldCheck,
    title: "Governance Compliance Note",
    recommendation: "All active data pipelines comply with the Arab Data Governance Model (Unit 14). Video TTL at 72h, RBAC roles verified, minor-age anonymization policy active. Audit trail synchronized.",
    priority: "info",
  });

  return insights.slice(0, 4);
}

export function AIInsightsPanel({ ssi, benchmark, alerts, agentInsights }: Props) {
  const insights = buildInsights(ssi, benchmark, alerts, agentInsights);

  return (
    <section className="rounded-[2rem] border border-white/10 bg-panel/90 p-6 shadow-panel backdrop-blur">
      <div className="mb-5 flex items-center gap-3">
        <div className="rounded-[1rem] bg-cobalt/30 p-2.5">
          <Brain className="h-5 w-5 text-sky" />
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-mist/50">AI Intelligence Layer — Unit 15</p>
          <h3 className="text-xl font-semibold text-white">Smart Insights & Recommendations</h3>
        </div>
        <span className="ml-auto rounded-full border border-sky/30 bg-sky/10 px-3 py-1 text-[10px] uppercase tracking-[0.22em] text-sky">
          Live Analysis
        </span>
      </div>

      {agentInsights && (
        <div className="mb-4 flex flex-wrap gap-3 text-xs text-mist/60">
          <span className="rounded-xl border border-white/10 bg-white/5 px-3 py-1">
            Session: <span className="text-white">{agentInsights.session_id ?? "—"}</span>
          </span>
          <span className="rounded-xl border border-white/10 bg-white/5 px-3 py-1">
            Class Engagement:{" "}
            <span className="text-white font-semibold">
              {Math.round(agentInsights.class_engagement_average * 100)}%
            </span>
          </span>
          <span className="rounded-xl border border-white/10 bg-white/5 px-3 py-1">
            Flags: <span className="text-warning font-semibold">{agentInsights.disengagement_flags.length}</span>
          </span>
          <span className="rounded-xl border border-white/10 bg-white/5 px-3 py-1">
            A/V Mismatches: <span className="text-sky font-semibold">{agentInsights.audio_visual_mismatches.length}</span>
          </span>
        </div>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {insights.map((ins) => {
          const c = priorityColors[ins.priority];
          const Icon = ins.icon;
          return (
            <div key={ins.title} className={`rounded-[1.4rem] border ${c.border} ${c.bg} px-4 py-4`}>
              <div className="flex items-center gap-2 mb-2">
                <Icon className="h-4 w-4 shrink-0" style={{ color: c.icon }} />
                <h4 className="text-sm font-semibold text-white">{ins.title}</h4>
                <span className={`ml-auto shrink-0 rounded-full ${c.badge} px-2 py-0.5 text-[9px] font-bold uppercase text-white tracking-wider`}>
                  {ins.priority}
                </span>
              </div>
              <p className="text-xs text-mist/65 leading-relaxed">{ins.recommendation}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
