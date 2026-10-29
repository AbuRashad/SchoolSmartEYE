from app.services import llm_agent_runtime


def test_provider_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("SCHOOLSMARTEYE_LLM_PROVIDER", raising=False)
    summary, used = llm_agent_runtime.generate_specialist_summary(
        "safety", "Review", {"attendance_rate": 95}, "deterministic summary"
    )
    assert summary == "deterministic summary"
    assert used is False


def test_missing_model_falls_back_without_network(monkeypatch):
    monkeypatch.setenv("SCHOOLSMARTEYE_LLM_PROVIDER", "ollama")
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    summary, used = llm_agent_runtime.generate_specialist_summary(
        "safety", "Review", {"attendance_rate": 95}, "deterministic summary"
    )
    assert summary == "deterministic summary"
    assert used is False


def test_orchestrator_marks_llm_only_when_summary_provider_succeeds(monkeypatch):
    from app.services import agent_orchestrator

    monkeypatch.setenv("SCHOOLSMARTEYE_LLM_PROVIDER", "ollama")
    monkeypatch.setattr(
        agent_orchestrator,
        "generate_specialist_summary",
        lambda agent_name, task, metrics, fallback_summary: (fallback_summary + " reviewed", True),
    )
    result = agent_orchestrator.run_orchestration("Review signals", {"attendance_rate": 95})
    assert result["provider"] == "ollama"
    assert all(stage["kind"] == "llm_assisted" for stage in result["stages"])
    assert result["requires_human_review"] is True
    assert result["autonomous_action_taken"] is False


def test_provider_failure_is_not_logged_and_falls_back(monkeypatch):
    from app.services import llm_agent_runtime

    monkeypatch.setenv("SCHOOLSMARTEYE_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "test-model")

    class BrokenClient:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def post(self, *args, **kwargs):
            raise llm_agent_runtime.httpx.ConnectError("unavailable")

    monkeypatch.setattr(llm_agent_runtime.httpx, "Client", BrokenClient)
    summary, used = llm_agent_runtime.generate_specialist_summary(
        "safety", "Review", {"attendance_rate": 95}, "deterministic summary"
    )
    assert summary == "deterministic summary"
    assert used is False
