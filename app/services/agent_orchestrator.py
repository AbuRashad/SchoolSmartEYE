"""Bounded multi-agent orchestration for SchoolSmartEYE."""
from __future__ import annotations

import uuid
from typing import Any

from app.services.agent_metric_scope import MAX_PEER_HANDOFF, scope_metrics
from app.services.llm_agent_runtime import ai_enabled, generate_specialist_analysis, last_outcome
from app.services.specialist_agents import (
    academic_agent, analytics_agent, ethics_review_agent, evidence_agent,
    operations_agent, safety_agent,
)

_ALLOWED_METRICS = {
    "attendance_rate", "total_students", "active_cameras", "total_units",
    "incidents_today", "incidents_week", "avg_crowd_density", "uptime_percent",
    "alerts_resolved_today", "patrol_efficiency", "compliance_score",
}
_METRIC_BOUNDS: dict[str, tuple[float, float]] = {
    "attendance_rate": (0, 100), "total_students": (0, float("inf")),
    "active_cameras": (0, float("inf")), "total_units": (0, float("inf")),
    "incidents_today": (0, float("inf")), "incidents_week": (0, float("inf")),
    "avg_crowd_density": (0, 1), "uptime_percent": (0, 100),
    "alerts_resolved_today": (0, float("inf")), "patrol_efficiency": (0, 100),
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


def _apply_ai_analysis(
    stages: list[dict[str, Any]], safe: dict[str, int | float]
) -> None:
    """Enrich stages with validated model analysis; deterministic findings stay authoritative.

    Each role receives only the metrics it owns, and the validated analyses of the
    roles that ran before it as bounded peer context. Every stage also records why
    its model call succeeded or fell back.
    """
    prior_analyses: list[dict[str, Any]] = []
    for stage in stages:
        name = str(stage["name"])
        analysis, used, provider = generate_specialist_analysis(
            agent_name=name,
            metrics=scope_metrics(name, safe),
            fallback_summary=stage.get("summary") or "No deterministic summary available.",
            prior_analyses=list(prior_analyses) if prior_analyses else None,
        )
        outcome = last_outcome()
        stage["agent_role"] = name
        stage["provider"] = provider if used else "deterministic"
        stage["analysis_status"] = "ai_completed" if used else "deterministic_fallback"
        stage["kind"] = "llm_assisted" if used else "deterministic"
        if outcome is not None:
            stage["failure_reason"] = outcome.failure_reason
            stage["latency_ms"] = outcome.total_latency_ms
            stage["attempts"] = [attempt.__dict__ for attempt in outcome.attempts]
        if used and analysis:
            stage["analysis"] = analysis
            stage["advisory_summary"] = analysis["summary"]
            prior_analyses.append({"agent": name, "analysis": analysis})
            prior_analyses = prior_analyses[-MAX_PEER_HANDOFF:]


def _fallback_diagnostic(reason: str) -> dict[str, Any]:
    """Per-stage diagnostics when the AI layer never ran at all."""
    return {"failure_reason": reason, "latency_ms": 0, "attempts": []}


def run_orchestration(task: str, metrics: dict[str, Any]) -> dict[str, Any]:
    """Run six specialist agents over allowlisted aggregates; require human review."""
    normalized_task = task.strip()
    if not normalized_task or len(normalized_task) > _MAX_TASK_LENGTH:
        raise ValueError(f"task must contain 1-{_MAX_TASK_LENGTH} characters")

    raw_data_status = metrics.get("data_status")
    data_status = raw_data_status if isinstance(raw_data_status, str) and raw_data_status in {"demo", "live"} else "unknown"
    raw_data_notice = metrics.get("data_notice")
    data_notice = raw_data_notice.strip()[:500] if isinstance(raw_data_notice, str) and raw_data_notice.strip() else (
        "These are illustrative demo metrics, not live school data." if data_status == "demo"
        else "Data provenance is unverified; confirm the source and freshness before operational use."
    )

    safe = _safe_metrics(metrics)
    evidence: list[dict[str, str | int | float]] = [
        {"source": "analytics.overview", "description": f"Aggregate metric: {key}", "value": value}
        for key, value in sorted(safe.items())
    ]
    stages = [
        analytics_agent(safe), safety_agent(safe), academic_agent(safe),
        operations_agent(safe), evidence_agent(evidence),
    ]
    stages.append(ethics_review_agent(safe, evidence, prior_stages=stages.copy()))

    if ai_enabled() and safe:
        _apply_ai_analysis(stages, safe)
    else:
        # Distinguish "AI turned off", "nothing to analyse" from a real failure.
        reason = "no_metrics" if not safe else "provider_disabled"
        for stage in stages:
            stage["agent_role"] = str(stage["name"])
            stage["provider"] = "deterministic"
            stage["analysis_status"] = "deterministic_fallback"
            stage.update(_fallback_diagnostic(reason))

    findings: list[dict[str, str]] = []
    for stage in stages:
        for field, label in (("flags", "flag"), ("recommendations", "recommendation"), ("warnings", "warning")):
            for item in stage.get(field, []):
                findings.append({"stage": str(stage["name"]), "type": label, "text": str(item)})

    limitations = [
        "Aggregate metrics do not establish individual causes or responsibility.",
        "All findings and recommendations require human review.",
        "AI analysis is advisory; deterministic findings and evidence remain authoritative.",
    ]
    limitations.append(data_notice if data_status != "live" else "Verify source provenance and metric freshness before operational use.")
    ai_count = sum(stage.get("analysis_status") == "ai_completed" for stage in stages)
    providers = sorted({stage["provider"] for stage in stages if stage.get("analysis_status") == "ai_completed"})
    # Surface why the AI layer produced nothing, without leaking internals per stage.
    fallback_reasons = sorted({
        str(stage.get("failure_reason")) for stage in stages
        if stage.get("analysis_status") != "ai_completed" and stage.get("failure_reason")
    })
    report = {
        "title": "School-wide specialist review",
        "status": "completed" if safe else "limited",
        "data_status": data_status, "data_notice": data_notice,
        "finding_count": len(findings), "findings": findings,
        "evidence_count": len(evidence), "limitations": limitations,
        "ai_agent_count": ai_count, "ai_providers": providers,
        "fallback_reasons": fallback_reasons,
        "reviewed_agents": stages[-1].get("reviewed_stages", []),
    }
    return {
        "request_id": str(uuid.uuid4()), "status": "completed" if safe else "limited",
        "task": normalized_task, "provider": providers[0] if len(providers) == 1 else ("hybrid" if providers else "deterministic"),
        "stages": stages, "evidence": evidence, "report": report,
        "confidence": "low" if not safe else "moderate",
        "requires_human_review": True, "autonomous_action_taken": False,
    }
