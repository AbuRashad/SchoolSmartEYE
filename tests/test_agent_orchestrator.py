from app.services.agent_orchestrator import run_orchestration


def test_six_native_specialists_run_without_external_provider():
    result = run_orchestration("Review school-wide indicators", {
        "attendance_rate": 88.5, "incidents_today": 2, "student_ids": ["private"],
    })
    assert [s["name"] for s in result["stages"]] == [
        "analytics", "safety", "academic", "operations", "evidence", "ethics_review"
    ]
    assert result["provider"] == "native"
    assert result["report"]["ai_agent_count"] == 6
    assert all(s["analysis_status"] == "native_completed" for s in result["stages"])
    assert all(s["provider"] == "native" for s in result["stages"])
    assert result["requires_human_review"] is True
    assert result["autonomous_action_taken"] is False
    assert "private" not in str(result)


def test_only_allowlisted_finite_numeric_aggregate_metrics_are_used():
    result = run_orchestration("Summarize", {
        "attendance_rate": 91.2, "student_name": "Private",
        "incidents_today": True, "avg_crowd_density": float("nan"),
    })
    assert [x["description"] for x in result["evidence"]] == ["Aggregate metric: attendance_rate"]


def test_task_validation_and_empty_data():
    import pytest
    with pytest.raises(ValueError):
        run_orchestration(" ", {})
    with pytest.raises(ValueError):
        run_orchestration("x" * 501, {})
    result = run_orchestration("Check readiness", {})
    assert result["status"] == "limited"
    assert result["confidence"] == "low"
    assert result["requires_human_review"] is True


def test_ethics_review_describes_native_role_agents_without_overclaiming_independence():
    result = run_orchestration("Review governance wording", {"attendance_rate": 95})
    ethics = result["stages"][-1]
    warning_text = " ".join(ethics.get("warnings", []))
    assert "six role-specific native analyses" in warning_text.lower()
    assert "not six independent trained models" in warning_text.lower()
    assert "deterministic findings remain authoritative" in warning_text.lower()
