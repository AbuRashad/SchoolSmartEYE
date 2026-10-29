"""Small, deterministic specialist agents used by the SchoolSmartEYE orchestrator.

Each specialist receives only validated aggregate metrics. This first iteration
uses transparent rules rather than an LLM; each result includes a bounded
summary or recommendations and never triggers an operational action.
"""
from __future__ import annotations

from typing import Any


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
    }


def safety_agent(metrics: dict[str, int | float]) -> dict[str, Any]:
    flags: list[str] = []
    attendance = metrics.get("attendance_rate")
    incidents = metrics.get("incidents_today")
    crowd = metrics.get("avg_crowd_density")
    if attendance is not None and attendance < 90:
        flags.append("Aggregate attendance is below the 90% review threshold; verify context.")
    if incidents is not None and incidents > 0:
        flags.append("The aggregate incident count is non-zero; review source reports.")
    if crowd is not None and crowd >= 0.75:
        flags.append("Aggregate crowd-density indicator is elevated; verify with staff.")
    return {
        "name": "safety",
        "kind": "deterministic",
        "status": "completed",
        "summary": f"Raised {len(flags)} aggregate safety review flag(s).",
        "flags": flags,
    }


def academic_agent(metrics: dict[str, int | float]) -> dict[str, Any]:
    actions = [
        "Review school-wide trends with educators before choosing an intervention.",
        "Use supportive, proportionate measures and evaluate their impact over time.",
    ]
    attendance = metrics.get("attendance_rate")
    if attendance is not None and attendance < 90:
        actions.append(
            "Explore attendance barriers and offer practical support; do not infer individual causes from aggregate data."
        )
    return {
        "name": "academic",
        "kind": "deterministic",
        "status": "completed",
        "summary": "Prepared supportive, school-level educational follow-up suggestions.",
        "recommendations": actions,
    }


def operations_agent(metrics: dict[str, int | float]) -> dict[str, Any]:
    flags: list[str] = []
    uptime = metrics.get("uptime_percent")
    cameras = metrics.get("active_cameras")
    if uptime is not None and uptime < 99:
        flags.append("Reported system uptime is below 99%; check service health and source freshness.")
    if cameras == 0:
        flags.append("No active cameras are reported; verify whether this is expected.")
    resolved = metrics.get("alerts_resolved_today")
    if resolved is not None:
        flags.append(f"Reported alerts resolved today: {resolved}.")
    return {
        "name": "operations",
        "kind": "deterministic",
        "status": "completed",
        "summary": "Reviewed available aggregate operational indicators.",
        "flags": flags,
    }


def evidence_agent(evidence: list[dict[str, str | int | float]]) -> dict[str, Any]:
    sources = sorted({str(item["source"]) for item in evidence})
    return {
        "name": "evidence",
        "kind": "deterministic",
        "status": "completed" if evidence else "limited",
        "summary": f"Attached {len(evidence)} validated evidence item(s) from {len(sources)} source(s).",
        "warnings": [] if evidence else ["No validated evidence items are available for this request."],
    }


def ethics_review_agent(metrics: dict[str, int | float], evidence: list[dict[str, str | int | float]]) -> dict[str, Any]:
    warnings = [
        "This v1 uses transparent deterministic rules, not independent LLM agents.",
        "The analytics overview may contain demo/static values; verify source freshness before operational use.",
        "Aggregate metrics cannot establish individual responsibility or explain causes.",
        "No student-level records or identifiers are passed into this orchestration pipeline.",
        "Human review is required before acting on any recommendation.",
        "Metrics outside expected domain bounds are excluded from evidence.",
    ]
    if not evidence:
        warnings.append("No usable metrics were supplied; conclusions are unavailable.")
    return {
        "name": "ethics_review",
        "kind": "deterministic",
        "status": "completed",
        "summary": "Checked evidence limitations and retained the human-review gate.",
        "warnings": warnings,
    }
