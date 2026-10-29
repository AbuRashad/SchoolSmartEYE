from app.services.agent_orchestrator import run_orchestration


def test_specialists_produce_distinct_domain_outputs():
    result = run_orchestration("Review school-wide signals", {
        "attendance_rate": 88,
        "incidents_today": 2,
        "avg_crowd_density": 0.8,
        "uptime_percent": 98,
        "active_cameras": 0,
        "alerts_resolved_today": 3,
    })
    stages = {stage["name"]: stage for stage in result["stages"]}

    assert len(stages) == 6
    assert stages["safety"]["flags"]
    assert stages["academic"]["recommendations"]
    assert stages["operations"]["flags"]
    assert stages["evidence"]["summary"].startswith("Attached")
    assert stages["ethics_review"]["warnings"]
    assert result["requires_human_review"] is True
    assert result["autonomous_action_taken"] is False


def test_specialists_handle_missing_metrics_without_fabricating_evidence():
    result = run_orchestration("Review status", {})
    stages = {stage["name"]: stage for stage in result["stages"]}

    assert result["status"] == "limited"
    assert result["evidence"] == []
    assert stages["analytics"]["status"] == "limited"
    assert stages["evidence"]["status"] == "limited"
    assert stages["safety"]["flags"] == []
    assert stages["operations"]["flags"] == []
