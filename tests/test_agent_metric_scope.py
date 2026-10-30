"""Tests for per-role metric scoping (stage 1).

These assert the two properties that matter: a role cannot see metrics outside
its scope, and the evidence/ethics roles retain the full picture.
"""
import pytest

from app.services import agent_orchestrator
from app.services.agent_metric_scope import (
    AGENT_METRIC_SCOPE,
    MAX_PEER_HANDOFF,
    metric_scope_for,
    scope_metrics,
    scoped_metric_names,
)

ALL_METRICS = {
    "attendance_rate": 88.0, "total_students": 400, "active_cameras": 12,
    "total_units": 20, "incidents_today": 2, "incidents_week": 7,
    "avg_crowd_density": 0.4, "uptime_percent": 99.5,
    "alerts_resolved_today": 5, "patrol_efficiency": 82.0, "compliance_score": 91.0,
}


def test_every_orchestrator_role_has_a_scope_entry():
    from app.services.llm_agent_runtime import AGENT_ROLES
    assert set(AGENT_METRIC_SCOPE) == set(AGENT_ROLES)


def test_roles_do_not_receive_metrics_outside_their_scope():
    assert scope_metrics("operations", ALL_METRICS) == {
        "active_cameras": 12, "total_units": 20, "uptime_percent": 99.5,
        "alerts_resolved_today": 5, "patrol_efficiency": 82.0,
    }
    assert scope_metrics("academic", ALL_METRICS) == {
        "attendance_rate": 88.0, "total_students": 400, "compliance_score": 91.0,
    }
    # A role must never see operational reliability data it does not own.
    assert "uptime_percent" not in scope_metrics("academic", ALL_METRICS)
    assert "attendance_rate" not in scope_metrics("operations", ALL_METRICS)


def test_evidence_and_ethics_retain_the_full_metric_set():
    for role in ("evidence", "ethics_review"):
        assert metric_scope_for(role) is None
        assert scope_metrics(role, ALL_METRICS) == ALL_METRICS


def test_unknown_role_is_unrestricted_not_empty():
    # A new role must not silently receive an empty payload.
    assert metric_scope_for("some_future_role") is None
    assert scope_metrics("some_future_role", ALL_METRICS) == ALL_METRICS


def test_scope_is_a_subset_of_the_allowlist():
    from app.services.agent_orchestrator import _ALLOWED_METRICS
    for role, scope in AGENT_METRIC_SCOPE.items():
        if scope is not None:
            unknown = scope - _ALLOWED_METRICS
            assert not unknown, f"{role} scopes unknown metrics: {sorted(unknown)}"


def test_no_two_restricted_roles_share_an_identical_scope():
    restricted = {
        role: frozenset(scope) for role, scope in AGENT_METRIC_SCOPE.items()
        if scope is not None
    }
    signatures = list(restricted.values())
    assert len(signatures) == len({frozenset(s) for s in signatures})


def test_scoped_names_helper_is_sorted_and_empty_for_full_scope():
    assert scoped_metric_names("operations") == sorted(scoped_metric_names("operations"))
    assert scoped_metric_names("evidence") == []


def test_orchestrator_sends_scoped_metrics_per_role(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "hybrid")
    captured = {}

    def fake_analysis(agent_name, metrics, fallback_summary, prior_analyses=None):
        captured[agent_name] = dict(metrics)
        return {"summary": "ok", "observations": [], "follow_up_questions": [], "risks": []}, True, "cloud"

    monkeypatch.setattr(agent_orchestrator, "generate_specialist_analysis", fake_analysis)
    agent_orchestrator.run_orchestration("Review aggregate signals", ALL_METRICS)

    assert set(captured) == set(AGENT_METRIC_SCOPE)
    assert "uptime_percent" not in captured["academic"]
    assert "attendance_rate" not in captured["operations"]
    # evidence and ethics still see everything
    assert captured["evidence"] == {
        k: v for k, v in ALL_METRICS.items() if k in captured["evidence"]
    }
    assert captured["ethics_review"] == {
        k: v for k, v in ALL_METRICS.items() if k in captured["ethics_review"]
    }


def test_deterministic_findings_are_unchanged_by_scoping(monkeypatch):
    """Scoping must not alter deterministic output, only the model payload."""
    metrics = {"attendance_rate": 85.0, "uptime_percent": 90.0, "incidents_today": 3}
    baseline = agent_orchestrator.run_orchestration("Review", metrics)

    monkeypatch.setenv("AI_PROVIDER", "hybrid")

    def fake_analysis(agent_name, metrics, fallback_summary, prior_analyses=None):
        return {"summary": "advisory", "observations": [], "follow_up_questions": [], "risks": []}, True, "cloud"

    monkeypatch.setattr(agent_orchestrator, "generate_specialist_analysis", fake_analysis)
    scoped = agent_orchestrator.run_orchestration("Review", metrics)

    assert baseline["report"]["findings"] == scoped["report"]["findings"]
    assert baseline["evidence"] == scoped["evidence"]
    assert baseline["report"]["evidence_count"] == scoped["report"]["evidence_count"]


def test_operations_agent_still_flags_uptime_deterministically(monkeypatch):
    """The operations finding depends on uptime_percent, which stays deterministic."""
    metrics = {"uptime_percent": 90.0, "active_cameras": 5}
    result = agent_orchestrator.run_orchestration("Review", metrics)
    operations = next(s for s in result["stages"] if s["name"] == "operations")
    assert any("uptime" in flag.lower() for flag in operations["flags"])


def test_peer_handoff_reaches_every_agent_after_the_first(monkeypatch):
    """Stage 1 also forwards prior analyses to all roles, not just ethics."""
    monkeypatch.setenv("AI_PROVIDER", "hybrid")
    seen = {}

    def fake_analysis(agent_name, metrics, fallback_summary, prior_analyses=None):
        seen[agent_name] = len(prior_analyses or [])
        return {"summary": f"analysis-{agent_name}", "observations": [], "follow_up_questions": [], "risks": []}, True, "cloud"

    monkeypatch.setattr(agent_orchestrator, "generate_specialist_analysis", fake_analysis)
    agent_orchestrator.run_orchestration("Review", {"attendance_rate": 90.0})

    assert seen["analytics"] == 0
    assert seen["safety"] == 1
    assert seen["academic"] == 2
    assert seen["operations"] == 3
    assert seen["evidence"] == 4
    assert seen["ethics_review"] == 5
    assert seen["ethics_review"] <= MAX_PEER_HANDOFF


def test_peer_handoff_is_bounded(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "hybrid")
    seen = {}

    def fake_analysis(agent_name, metrics, fallback_summary, prior_analyses=None):
        seen[agent_name] = prior_analyses
        return {"summary": "ok", "observations": [], "follow_up_questions": [], "risks": []}, True, "cloud"

    monkeypatch.setattr(agent_orchestrator, "generate_specialist_analysis", fake_analysis)
    agent_orchestrator.run_orchestration("Review", {"attendance_rate": 90.0})
    assert len(seen["ethics_review"]) <= MAX_PEER_HANDOFF


def test_peer_handoff_carries_only_validated_analysis_fields(monkeypatch):
    """Peer context must not leak deterministic findings into the model payload."""
    monkeypatch.setenv("AI_PROVIDER", "hybrid")
    seen = {}

    def fake_analysis(agent_name, metrics, fallback_summary, prior_analyses=None):
        seen[agent_name] = prior_analyses
        return {"summary": "ok", "observations": [], "follow_up_questions": [], "risks": []}, True, "cloud"

    monkeypatch.setattr(agent_orchestrator, "generate_specialist_analysis", fake_analysis)
    agent_orchestrator.run_orchestration("Review", {"attendance_rate": 85.0, "incidents_today": 2})
    for entry in seen["ethics_review"]:
        assert set(entry) == {"agent", "analysis"}
        assert set(entry["analysis"]) == {"summary", "observations", "follow_up_questions", "risks"}
