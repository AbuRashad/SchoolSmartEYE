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


def test_metrics_outside_domain_bounds_are_excluded():
    result = run_orchestration("Validate aggregate metrics", {
        "attendance_rate": 140,
        "uptime_percent": -1,
        "avg_crowd_density": 1.5,
        "incidents_today": -3,
        "total_students": 12.5,
        "active_cameras": 4,
        "compliance_score": 100,
    })

    assert {item["description"] for item in result["evidence"]} == {
        "Aggregate metric: active_cameras",
        "Aggregate metric: compliance_score",
    }
    ethics = next(stage for stage in result["stages"] if stage["name"] == "ethics_review")
    assert any("outside expected domain bounds" in warning for warning in ethics["warnings"])


def test_metric_bounds_accept_valid_edge_values():
    result = run_orchestration("Check boundary values", {
        "attendance_rate": 0,
        "uptime_percent": 100,
        "avg_crowd_density": 1,
        "incidents_today": 0,
        "total_students": 0,
    })

    assert {item["description"] for item in result["evidence"]} == {
        "Aggregate metric: attendance_rate",
        "Aggregate metric: uptime_percent",
        "Aggregate metric: avg_crowd_density",
        "Aggregate metric: incidents_today",
        "Aggregate metric: total_students",
    }


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
