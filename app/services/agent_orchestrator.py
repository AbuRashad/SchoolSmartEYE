"""Bounded, deterministic orchestration for SchoolSmartEYE.

This v1 deliberately does not call an LLM or access student-level records.
Specialists are deterministic analysis stages; the review stage always requires
human review for safety-related recommendations.
"""
from __future__ import annotations

from typing import Any
import uuid

# Explicit allowlist: only aggregate operational metrics can enter the pipeline.
_ALLOWED_METRICS = {
    "attendance_rate",
    "total_students",
    "active_cameras",
    "total_units",
    "incidents_today",
    "incidents_week",
    "avg_crowd_density",
    "uptime_percent",
    "alerts_resolved_today",
    "patrol_efficiency",
    "compliance_score",
}
# Plausible domain bounds prevent malformed numeric values from becoming evidence.
# Density is a normalized ratio (0..1); *_percent / rates are percentages (0..100).
_METRIC_BOUNDS: dict[str, tuple[float, float]] = {
    "attendance_rate": (0, 100),
    "total_students": (0, float("inf")),
    "active_cameras": (0, float("inf")),
    "total_units": (0, float("inf")),
    "incidents_today": (0, float("inf")),
    "incidents_week": (0, float("inf")),
    "avg_crowd_density": (0, 1),
    "uptime_percent": (0, 100),
    "alerts_resolved_today": (0, float("inf")),
    "patrol_efficiency": (0, 100),
    "compliance_score": (0, 100),
}
_INTEGER_METRICS = {
    "total_students",
    "active_cameras",
    "total_units",
    "incidents_today",
    "incidents_week",
    "alerts_resolved_today",
}
_MAX_TASK_LENGTH = 500


def _safe_metrics(metrics: dict[str, Any]) -> dict[str, int | float]:
    safe: dict[str, int | float] = {}
    for key in _ALLOWED_METRICS:
        value = metrics.get(key)
        # Reject booleans, strings, nested objects, NaN, and infinities.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if value != value or value in (float("inf"), float("-inf")):
            continue
        minimum, maximum = _METRIC_BOUNDS[key]
        if not minimum <= value <= maximum:
            continue
        if key in _INTEGER_METRICS and value % 1 != 0:
            continue
        safe[key] = value
    return safe


def run_orchestration(task: str, metrics: dict[str, Any]) -> dict[str, Any]:
    """Run a bounded four-stage deterministic pipeline on aggregate metrics only."""
    normalized_task = task.strip()
    if not normalized_task or len(normalized_task) > _MAX_TASK_LENGTH:
        raise ValueError(f"task must contain 1-{_MAX_TASK_LENGTH} characters")

    safe = _safe_metrics(metrics)
    evidence: list[dict[str, str | int | float]] = [
        {"source": "analytics.overview", "description": f"Aggregate metric: {key}", "value": value}
        for key, value in sorted(safe.items())
    ]

    # Stage 1 — Analytics: report only aggregate values that are actually present.
    analytics_summary = (
        f"Reviewed {len(safe)} allowlisted aggregate operational metrics."
        if safe
        else "No valid aggregate metrics were available; analysis is limited."
    )

    # Stage 2 — Safety: deterministic flags, not incident findings or accusations.
    safety_flags: list[str] = []
    attendance = safe.get("attendance_rate")
    if attendance is not None and attendance < 90:
        safety_flags.append("Aggregate attendance is below the 90% review threshold.")
    incidents = safe.get("incidents_today")
    if incidents is not None and incidents > 0:
        safety_flags.append("The aggregate incident count is non-zero; review the underlying reports.")
    crowd = safe.get("avg_crowd_density")
    if crowd is not None and crowd >= 0.75:
        safety_flags.append("Aggregate crowd-density indicator is elevated; verify with staff.")

    # Stage 3 — Education: supportive, non-stigmatizing operational next steps.
    education_actions = [
        "Review aggregate trends with relevant staff before selecting an intervention.",
        "Prefer supportive, proportionate measures and evaluate their impact over time.",
    ]
    if attendance is not None and attendance < 90:
        education_actions.append(
            "Explore school-wide attendance barriers and offer practical support; do not infer individual causes from aggregate data."
        )

    # Stage 4 — Ethics/review: explicit uncertainty and human-in-the-loop gate.
    warnings = [
        "This v1 uses deterministic rules, not independent LLM agents.",
        "The repository's current analytics overview contains demo/static values; verify source freshness before operational use.",
        "Aggregate metrics cannot establish individual responsibility or explain causes.",
        "No student-level records or identifiers were passed into the orchestration pipeline.",
        "Metrics outside expected domain bounds are excluded from evidence.",
    ]
    if not safe:
        warnings.append("No usable metrics were supplied; conclusions are unavailable.")

    return {
        "request_id": str(uuid.uuid4()),
        "status": "completed" if safe else "limited",
        "task": normalized_task,
        "provider": "deterministic",
        "stages": [
            {"name": "analytics", "kind": "deterministic", "status": "completed" if safe else "limited", "summary": analytics_summary},
            {"name": "safety", "kind": "deterministic", "status": "completed", "flags": safety_flags},
            {"name": "education", "kind": "deterministic", "status": "completed", "recommendations": education_actions},
            {"name": "ethics_review", "kind": "deterministic", "status": "completed", "warnings": warnings},
        ],
        "evidence": evidence,
        "confidence": "low" if not safe else "moderate",
        "requires_human_review": True,
        "autonomous_action_taken": False,
    }
