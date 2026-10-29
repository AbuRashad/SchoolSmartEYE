""""Bounded multi-agent orchestration for SchoolSmartEYE.

Specialists receive validated aggregate metrics only. Optional LLM summaries are
advisory; deterministic findings and evidence remain authoritative. Human review
is mandatory and agents cannot trigger operational actions.
"""
from __future__ import annotations

import uuid
from typing import Any

from app.services.llm_agent_runtime import generate_specialist_summary, ollama_enabled
from app.services.specialist_agents import (
    academic_agent,
    analytics_agent,
    ethics_review_agent,
    evidence_agent,
    operations_agent,
    safety_agent,
)

_ALLOWED_METRICS = {
    "attendance_rate", "total_students", "active_cameras", "total_units",
    "incidents_today", "incidents_week", "avg_crowd_density",
    "uptime_percent", "alerts_resolved_today", "patrol_efficiency",
    "compliance_score",
}
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
    "total_students", "active_cameras", "total_units", "incidents_today",
    "incidents_week", "alerts_resolved_today",
}
_MAX_TASK_LENGTH = 500


def _safe_metrics(metrics: dict[str, Any]) -> dict[str, int | float]:
    """Allow only finite, numeric aggregate metrics within domain bounds."""
    safe: dict[str, int | float] = {}
    for key in _ALLOWED_METRICS:
        value = metrics.get(key)
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
    """Run six specialists; optionally enrich summaries through Ollama."""
    normalized_task = task.strip()
    if not normalized_task or len(normalized_task) > _MAX_TASK_LENGTH:
        raise ValueError(f"task must contain 1-{_MAX_TASK_LENGTH} characters")

    safe = _safe_metrics(metrics)
    evidence: list[dict[str, str | int | float]] = [
        {"source": "analytics.overview", "description": f"Aggregate metric: {key}", "value": value}
        for key, value in sorted(safe.items())
    ]
    stages = [
        analytics_agent(safe),
        safety_agent(safe),
        academic_agent(safe),
        operations_agent(safe),
        evidence_agent(evidence),
        ethics_review_agent(safe, evidence),
    ]

    llm_used = False
    if ollama_enabled() and safe:
        for stage in stages:
            summary, used = generate_specialist_summary(
                agent_name=stage["name"],
                metrics=safe,
                fallback_summary=stage.get("summary") or "No summary available.",
            )
            stage["summary"] = summary
            stage["kind"] = "llm_assisted" if used else "deterministic"
            llm_used = llm_used or used

    return {
        "request_id": str(uuid.uuid4()),
        "status": "completed" if safe else "limited",
        "task": normalized_task,
        "provider": "ollama" if llm_used else "deterministic",
        "stages": stages,
        "evidence": evidence,
        "confidence": "low" if not safe else "moderate",
        "requires_human_review": True,
        "autonomous_action_taken": False,
    }
