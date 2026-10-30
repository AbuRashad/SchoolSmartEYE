from app.services import llm_agent_runtime


def test_native_engine_is_enabled_without_external_provider_configuration(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("AI_CLOUD_BASE_URL", raising=False)
    monkeypatch.delenv("AI_LOCAL_BASE_URL", raising=False)

    result, used, provider = llm_agent_runtime.generate_specialist_analysis(
        "safety", {"incidents_today": 2, "avg_crowd_density": 0.8}, "fallback"
    )

    assert used is True
    assert provider == "native"
    assert result["summary"].startswith("Native safety reasoning")
    assert result["risks"]


def test_unknown_agent_is_rejected():
    result, used, provider = llm_agent_runtime.generate_specialist_analysis(
        "unknown", {"attendance_rate": 95}, "fallback"
    )
    assert result is None and used is False and provider is None


def test_external_provider_environment_does_not_enable_network_calls(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "hybrid")
    monkeypatch.setenv("AI_CLOUD_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("AI_CLOUD_MODEL", "external-model")
    monkeypatch.setenv("AI_CLOUD_API_KEY", "must-not-be-used")
    monkeypatch.setenv("AI_LOCAL_BASE_URL", "http://127.0.0.1:8081/v1")

    result, used, provider = llm_agent_runtime.generate_specialist_analysis(
        "safety", {"attendance_rate": 95}, "fallback"
    )

    assert used is True
    assert provider == "native"
    assert result is not None
    assert not hasattr(llm_agent_runtime, "httpx")
    assert not hasattr(llm_agent_runtime, "_provider_configs")


def test_native_analysis_has_bounded_structured_fields():
    result, used, provider = llm_agent_runtime.generate_specialist_analysis(
        "analytics", {"attendance_rate": 88, "incidents_today": 1}, "fallback"
    )
    assert used is True and provider == "native"
    assert set(result) == {"summary", "observations", "follow_up_questions", "risks"}
    assert len(result["summary"]) <= 500
    assert all(isinstance(result[key], list) and len(result[key]) <= 5
               for key in ("observations", "follow_up_questions", "risks"))
    assert all(len(item) <= 240 for key in ("observations", "follow_up_questions", "risks")
               for item in result[key])


def test_each_agent_has_a_distinct_specialist_mission():
    roles = llm_agent_runtime.AGENT_ROLES
    assert set(roles) == {"analytics", "safety", "academic", "operations", "evidence", "ethics_review"}
    assert len(set(roles.values())) == 6
    assert "privacy" in roles["ethics_review"].lower()


def test_agent_receives_only_aggregate_metrics_and_ethics_gets_peer_handoff(monkeypatch):
    from app.services import agent_orchestrator

    captured = []

    def fake_analysis(agent_name, metrics, fallback_summary, prior_analyses=None):
        captured.append({"agent": agent_name, "metrics": dict(metrics), "prior": prior_analyses})
        return {
            "summary": f"Native review for {agent_name}",
            "observations": ["Review aggregate trend"],
            "follow_up_questions": [],
            "risks": [],
        }, True, "native"

    monkeypatch.setattr(agent_orchestrator, "generate_specialist_analysis", fake_analysis)
    result = agent_orchestrator.run_orchestration("Review school aggregate signals", {
        "attendance_rate": 92,
        "student_ids": ["PRIVATE-STUDENT-123"],
        "student_names": ["Private Person"],
    })

    assert len(captured) == 6
    assert all("student_ids" not in item["metrics"] and "student_names" not in item["metrics"]
               for item in captured)
    assert all("PRIVATE-STUDENT-123" not in str(item) for item in captured)
    assert captured[-1]["agent"] == "ethics_review" and len(captured[-1]["prior"]) == 5
    assert result["report"]["ai_agent_count"] == 6
    assert result["provider"] == "native"
    assert all(stage["analysis_status"] == "native_completed" for stage in result["stages"])
    assert result["requires_human_review"] is True
    assert result["autonomous_action_taken"] is False


def test_task_text_never_reaches_native_agent(monkeypatch):
    from app.services import agent_orchestrator

    captured = []

    def fake_analysis(agent_name, metrics, fallback_summary, prior_analyses=None):
        captured.append(str(metrics) + str(prior_analyses))
        return {
            "summary": "safe",
            "observations": [],
            "follow_up_questions": [],
            "risks": [],
        }, True, "native"

    monkeypatch.setattr(agent_orchestrator, "generate_specialist_analysis", fake_analysis)
    agent_orchestrator.run_orchestration("DO-NOT-SEND-THIS-TASK", {"attendance_rate": 95})
    assert all("DO-NOT-SEND-THIS-TASK" not in payload for payload in captured)
