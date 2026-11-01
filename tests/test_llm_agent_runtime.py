from app.services import llm_agent_runtime


def test_provider_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("AI_CLOUD_BASE_URL", raising=False)
    monkeypatch.delenv("AI_LOCAL_BASE_URL", raising=False)
    result, used, provider = llm_agent_runtime.generate_specialist_analysis("safety", {"attendance_rate": 95}, "fallback")
    assert result is None and used is False and provider is None


def test_unknown_agent_and_missing_model_fall_back(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "hybrid")
    monkeypatch.setenv("AI_CLOUD_BASE_URL", "https://api.example.test/v1")
    monkeypatch.delenv("AI_CLOUD_MODEL", raising=False)
    monkeypatch.delenv("AI_LOCAL_BASE_URL", raising=False)
    result, used, provider = llm_agent_runtime.generate_specialist_analysis("unknown", {"attendance_rate": 95}, "fallback")
    assert result is None and used is False and provider is None
    result, used, provider = llm_agent_runtime.generate_specialist_analysis("safety", {"attendance_rate": 95}, "fallback")
    assert result is None and used is False and provider is None


def test_structured_analysis_is_parsed():
    parsed = llm_agent_runtime._parse_analysis(
        '{"summary":"Risk review","observations":["Check source"],'
        '"follow_up_questions":["Is data current?"],"risks":["False positive"]}'
    )
    assert parsed == {
        "summary": "Risk review",
        "observations": ["Check source"],
        "follow_up_questions": ["Is data current?"],
        "risks": ["False positive"],
    }


def test_malformed_or_invalid_structured_output_is_rejected():
    parser = llm_agent_runtime._parse_analysis
    assert parser("not json") is None
    assert parser('{"observations":"not a list","summary":"x","follow_up_questions":[],"risks":[]}') is None
    assert parser('{"summary":"","observations":[],"follow_up_questions":[],"risks":[]}') is None
    assert parser('{"summary":"x","observations":[],"follow_up_questions":[]}') is None
    assert parser('{"summary":"x","observations":[],"follow_up_questions":[],"risks":[],"extra":"x"}') is None


def test_oversized_content_and_fields_are_rejected_not_truncated():
    parser = llm_agent_runtime._parse_analysis
    assert parser(" " * (llm_agent_runtime.MAX_RESPONSE_CHARS + 1)) is None
    oversized_summary = "s" * (llm_agent_runtime.MAX_SUMMARY_LENGTH + 1)
    body = {"summary": oversized_summary, "observations": [], "follow_up_questions": [], "risks": []}
    import json
    assert parser(json.dumps(body)) is None
    oversized_item = "x" * (llm_agent_runtime.MAX_ITEM_LENGTH + 1)
    body["summary"] = "valid"
    body["observations"] = [oversized_item]
    assert parser(json.dumps(body)) is None
    body["observations"] = ["x"] * (llm_agent_runtime.MAX_ITEMS + 1)
    assert parser(json.dumps(body)) is None


def test_each_agent_has_a_distinct_specialist_mission():
    roles = llm_agent_runtime.AGENT_ROLES
    assert set(roles) == {"analytics", "safety", "academic", "operations", "evidence", "ethics_review"}
    assert len(set(roles.values())) == 6
    assert "privacy" in roles["ethics_review"].lower()


def test_cloud_failure_falls_back_to_local(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "hybrid")
    monkeypatch.setenv("AI_CLOUD_BASE_URL", "https://cloud.example.test/v1")
    monkeypatch.setenv("AI_CLOUD_MODEL", "cloud-model")
    monkeypatch.setenv("AI_CLOUD_API_KEY", "test-secret")
    monkeypatch.setenv("AI_LOCAL_BASE_URL", "http://127.0.0.1:8081/v1")
    monkeypatch.setenv("AI_LOCAL_MODEL", "local-model")
    calls = []

    class FakeResponse:
        def __init__(self, content=None, fail=False):
            self.content, self.fail = content, fail
        def raise_for_status(self):
            if self.fail:
                raise llm_agent_runtime.httpx.ConnectError("unavailable")
        def json(self):
            return {"choices": [{"message": {"content": self.content}}]}

    class FakeClient:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def post(self, url, headers=None, json=None):
            calls.append((url, headers, json))
            if "cloud.example.test" in url:
                return FakeResponse(fail=True)
            return FakeResponse('{"summary":"Local result","observations":[],"follow_up_questions":[],"risks":[]}')

    monkeypatch.setattr(llm_agent_runtime.httpx, "Client", FakeClient)
    result, used, provider = llm_agent_runtime.generate_specialist_analysis(
        "safety", {"attendance_rate": 95}, "fallback"
    )
    assert used is True and provider == "local"
    assert result["summary"] == "Local result"
    assert len(calls) == 2
    assert calls[0][1]["Authorization"] == "Bearer test-secret"
    assert calls[1][2]["model"] == "local-model"


def test_cloud_is_rejected_without_https(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "cloud")
    monkeypatch.setenv("AI_CLOUD_BASE_URL", "http://unsafe.example.test/v1")
    monkeypatch.setenv("AI_CLOUD_MODEL", "model")
    assert llm_agent_runtime._provider_configs() == []


def test_provider_failure_falls_back(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "local")
    monkeypatch.setenv("AI_LOCAL_BASE_URL", "http://127.0.0.1:8081/v1")
    monkeypatch.setenv("AI_LOCAL_MODEL", "test-model")

    class BrokenClient:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def post(self, *args, **kwargs):
            raise llm_agent_runtime.httpx.ConnectError("unavailable")

    monkeypatch.setattr(llm_agent_runtime.httpx, "Client", BrokenClient)
    result, used, provider = llm_agent_runtime.generate_specialist_analysis("safety", {"attendance_rate": 95}, "fallback")
    assert result is None and used is False and provider is None


def test_agent_receives_only_aggregate_metrics_and_ethics_gets_peer_handoff(monkeypatch):
    from app.services import agent_orchestrator
    monkeypatch.setenv("AI_PROVIDER", "hybrid")
    captured = []

    def fake_analysis(agent_name, metrics, fallback_summary, prior_analyses=None):
        captured.append({"agent": agent_name, "metrics": dict(metrics), "prior": prior_analyses})
        return {"summary": f"AI review for {agent_name}", "observations": ["Review aggregate trend"],
                "follow_up_questions": [], "risks": []}, True, "cloud"

    monkeypatch.setattr(agent_orchestrator, "generate_specialist_analysis", fake_analysis)
    result = agent_orchestrator.run_orchestration("Review PRIVATE-STUDENT-123 record", {
        "attendance_rate": 92, "student_ids": ["PRIVATE-STUDENT-123"], "student_names": ["Private Person"],
    })
    assert len(captured) == 6
    assert all("student_ids" not in item["metrics"] and "student_names" not in item["metrics"] for item in captured)
    assert all("PRIVATE-STUDENT-123" not in str(item) for item in captured)
    assert captured[-1]["agent"] == "ethics_review" and len(captured[-1]["prior"]) == 5
    assert result["report"]["ai_agent_count"] == 6
    assert result["provider"] == "cloud"
    assert all(stage["analysis_status"] == "ai_completed" for stage in result["stages"])
    assert result["requires_human_review"] is True and result["autonomous_action_taken"] is False


def test_task_text_never_reaches_agent_provider(monkeypatch):
    from app.services import agent_orchestrator
    monkeypatch.setenv("AI_PROVIDER", "hybrid")
    captured = []

    def fake_analysis(agent_name, metrics, fallback_summary, prior_analyses=None):
        captured.append(str(metrics) + str(prior_analyses))
        return {"summary": "safe", "observations": [], "follow_up_questions": [], "risks": []}, True, "local"

    monkeypatch.setattr(agent_orchestrator, "generate_specialist_analysis", fake_analysis)
    agent_orchestrator.run_orchestration("DO-NOT-SEND-THIS-TASK", {"attendance_rate": 95})
    assert all("DO-NOT-SEND-THIS-TASK" not in payload for payload in captured)
