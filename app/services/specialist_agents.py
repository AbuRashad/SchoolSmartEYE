"""Small, deterministic specialist agents used by the SchoolSmartEYE orchestrator.

Each specialist receives only validated aggregate metrics. This first iteration
uses transparent rules rather than an LLM; each result includes a bounded
summary or recommendations and never triggers an operational action.

Review thresholds are no longer hardcoded here. They live in
`app.core.policy_thresholds` so a policy change happens in one place and every
decision can report the threshold and policy version it was made against.
"""
from __future__ import annotations

from typing import Any

from app.core.policy_thresholds import (
    ATTENDANCE_REVIEW,
    CROWD_DENSITY_ELEVATED,
    INCIDENTS_TODAY_REVIEW,
    PATROL_EFFICIENCY_REVIEW,
    POLICY_VERSION,
    UPTIME_REVIEW,
)


def _numeric(metrics: dict[str, int | float], key: str) -> int | float | None:
    """Read a metric as a number, ignoring booleans and non-numeric values."""
    value = metrics.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def analytics_agent(metrics: dict[str, int | float]) -> dict[str, Any]:
    return {
        "name": "analytics",
        "kind": "deterministic",
        "status": "completed" if metrics else "limited",
        "summary": (
            f"Reviewed {len(metrics)} validated aggregate metrics."
            if metrics
            else "No validated aggregate metrics were available."
        ),
        "policy_version": POLICY_VERSION,
    }


def safety_agent(metrics: dict[str, int | float]) -> dict[str, Any]:
    flags: list[str] = []
    threshold_refs: list[str] = []
    attendance = _numeric(metrics, "attendance_rate")
    incidents = _numeric(metrics, "incidents_today")
    crowd = _numeric(metrics, "avg_crowd_density")
    if attendance is not None and ATTENDANCE_REVIEW.breached_by(attendance):
        flags.append(
            f"Aggregate attendance is below the {ATTENDANCE_REVIEW.value:g}% review "
            "threshold; verify context."
        )
        threshold_refs.append(ATTENDANCE_REVIEW.describe(attendance))
    if incidents is not None and INCIDENTS_TODAY_REVIEW.breached_by(incidents):
        flags.append("The aggregate incident count is non-zero; review source reports.")
        threshold_refs.append(INCIDENTS_TODAY_REVIEW.describe(incidents))
    # Crowd density is treated as elevated at or above the threshold.
    if crowd is not None and (crowd >= CROWD_DENSITY_ELEVATED.value):
        flags.append(
            f"Aggregate crowd-density indicator is at or above "
            f"{CROWD_DENSITY_ELEVATED.value:g}; verify with staff."
        )
        threshold_refs.append(CROWD_DENSITY_ELEVATED.describe(crowd))
    return {
        "name": "safety",
        "kind": "deterministic",
        "status": "completed",
        "summary": f"Raised {len(flags)} aggregate safety review flag(s).",
        "flags": flags,
        "threshold_refs": threshold_refs,
        "policy_version": POLICY_VERSION,
    }


def academic_agent(metrics: dict[str, int | float]) -> dict[str, Any]:
    actions = [
        "Review school-wide trends with educators before choosing an intervention.",
        "Use supportive, proportionate measures and evaluate their impact over time.",
    ]
    threshold_refs: list[str] = []
    attendance = _numeric(metrics, "attendance_rate")
    if attendance is not None and ATTENDANCE_REVIEW.breached_by(attendance):
        actions.append(
            "Explore attendance barriers and offer practical support; do not infer "
            "individual causes from aggregate data."
        )
        threshold_refs.append(ATTENDANCE_REVIEW.describe(attendance))
    return {
        "name": "academic",
        "kind": "deterministic",
        "status": "completed",
        "summary": "Prepared supportive, school-level educational follow-up suggestions.",
        "recommendations": actions,
        "threshold_refs": threshold_refs,
        "policy_version": POLICY_VERSION,
    }


def operations_agent(metrics: dict[str, int | float]) -> dict[str, Any]:
    flags: list[str] = []
    threshold_refs: list[str] = []
    uptime = _numeric(metrics, "uptime_percent")
    cameras = _numeric(metrics, "active_cameras")
    efficiency = _numeric(metrics, "patrol_efficiency")
    if uptime is not None and UPTIME_REVIEW.breached_by(uptime):
        flags.append(
            f"Reported system uptime is below {UPTIME_REVIEW.value:g}%; check service "
            "health and source freshness."
        )
        threshold_refs.append(UPTIME_REVIEW.describe(uptime))
    if cameras == 0:
        flags.append("No active cameras are reported; verify whether this is expected.")
    if efficiency is not None and PATROL_EFFICIENCY_REVIEW.breached_by(efficiency):
        flags.append(
            f"Reported patrol efficiency is below "
            f"{PATROL_EFFICIENCY_REVIEW.value:g}%; review operational coverage."
        )
        threshold_refs.append(PATROL_EFFICIENCY_REVIEW.describe(efficiency))
    resolved = _numeric(metrics, "alerts_resolved_today")
    if resolved is not None:
        flags.append(f"Reported alerts resolved today: {resolved}.")
    return {
        "name": "operations",
        "kind": "deterministic",
        "status": "completed",
        "summary": "Reviewed available aggregate operational indicators.",
        "flags": flags,
        "threshold_refs": threshold_refs,
        "policy_version": POLICY_VERSION,
    }


def evidence_agent(evidence: list[dict[str, str | int | float]]) -> dict[str, Any]:
    sources = sorted({str(item["source"]) for item in evidence})
    return {
        "name": "evidence",
        "kind": "deterministic",
        "status": "completed" if evidence else "limited",
        "summary": f"Attached {len(evidence)} validated evidence item(s) from {len(sources)} source(s).",
        "warnings": [] if evidence else ["No validated evidence items are available for this request."],
        "policy_version": POLICY_VERSION,
    }


def ethics_review_agent(
    metrics: dict[str, int | float],
    evidence: list[dict[str, str | int | float]],
    prior_stages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Cross-review completed specialist outputs without changing their findings."""
    warnings = [
        "This v1 uses transparent deterministic rules, not independent LLM agents.",
        "The analytics overview may contain demo/static values; verify source freshness before operational use.",
        "Aggregate metrics cannot establish individual responsibility or explain causes.",
        "No student-level records or identifiers are passed into this orchestration pipeline.",
        "Human review is required before acting on any recommendation.",
        "Metrics outside expected domain bounds are excluded from evidence.",
        f"Findings were evaluated against policy {POLICY_VERSION}; thresholds may change over time.",
    ]
    reviewed = prior_stages or []
    reviewed_names = [str(stage.get("name", "unknown")) for stage in reviewed]
    incomplete = [
        str(stage.get("name", "unknown"))
        for stage in reviewed
        if stage.get("status") != "completed" or not stage.get("summary")
    ]
    if not evidence:
        warnings.append("No usable metrics were supplied; conclusions are unavailable.")
    if not reviewed:
        warnings.append("No prior specialist outputs were available for cross-review.")
    if incomplete:
        warnings.append(
            "Cross-review found incomplete specialist output(s): " + ", ".join(incomplete) + "."
        )
    return {
        "name": "ethics_review",
        "kind": "deterministic",
        "status": "completed",
        "summary": "Cross-reviewed prior specialist outputs and evidence limitations; human review remains required.",
        "reviewed_stages": reviewed_names,
        "warnings": warnings,
        "policy_version": POLICY_VERSION,
    }
