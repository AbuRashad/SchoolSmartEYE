from app.services.agent_orchestrator import run_orchestration


def test_orchestrator_runs_four_ordered_stages_and_requires_human_review():
    result = run_orchestration("Review today's school-wide signals", {
        "attendance_rate": 88.5,
        "incidents_today": 2,
        "student_names": ["Synthetic Student"],
        "student_ids": ["student-123"],
    })

    assert [stage["name"] for stage in result["stages"]] == [
        "analytics", "safety", "education", "ethics_review"
    ]
    assert result["requires_human_review"] is True
    assert result["autonomous_action_taken"] is False
    assert result["provider"] == "deterministic"
    assert all("student_names" not in item and "student_ids" not in item for item in result["evidence"])
    assert all("Synthetic Student" not in str(item) and "student-123" not in str(item) for item in result["evidence"])


def test_only_allowlisted_numeric_aggregate_metrics_enter_evidence():
    result = run_orchestration("Summarize", {
        "attendance_rate": 91.2,
        "student_name": "Private",
        "student_count": {"raw": "nested"},
        "incidents_today": True,
        "avg_crowd_density": float("nan"),
    })
    assert [item["source"] for item in result["evidence"]] == ["analytics.overview"]
    assert [item["description"] for item in result["evidence"]] == ["Aggregate metric: attendance_rate"]


def test_empty_metrics_returns_limited_result_and_never_claims_confidence():
    result = run_orchestration("Check readiness", {})
    assert result["status"] == "limited"
    assert result["confidence"] == "low"
    assert result["evidence"] == []
    assert result["requires_human_review"] is True


def test_task_validation_rejects_blank_and_oversized_requests():
    import pytest

    with pytest.raises(ValueError):
        run_orchestration("   ", {})
    with pytest.raises(ValueError):
        run_orchestration("x" * 501, {})
