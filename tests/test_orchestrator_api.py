from fastapi.testclient import TestClient


def test_orchestrator_requires_authentication(anon_client: TestClient):
    response = anon_client.post(
        "/api/v1/agent/orchestrate",
        json={"task": "Review aggregate school signals"},
    )
    assert response.status_code == 401


def test_teacher_cannot_call_principal_ministry_orchestrator(auth_headers):
    from app.main import app

    client = TestClient(app, headers=auth_headers("teacher"))
    response = client.post(
        "/api/v1/agent/orchestrate",
        json={"task": "Review aggregate school signals"},
    )
    assert response.status_code == 403


def test_orchestrator_uses_authenticated_school_scoped_analytics(client: TestClient):
    from app.services import seed_data

    seed_data.populate()
    response = client.post(
        "/api/v1/agent/orchestrate",
        json={"task": "Review aggregate school signals"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] in {"deterministic", "ollama"}
    assert payload["requires_human_review"] is True
    assert payload["autonomous_action_taken"] is False
    assert [stage["name"] for stage in payload["stages"]] == [
        "analytics", "safety", "academic", "operations", "evidence", "ethics_review",
    ]
    assert payload["report"]["data_status"] == "demo"
    assert "not live school telemetry" in payload["report"]["data_notice"]


def test_orchestrator_rejects_unknown_request_fields(client: TestClient):
    response = client.post(
        "/api/v1/agent/orchestrate",
        json={"task": "Review aggregate school signals", "student_ids": ["private-id"]},
    )
    assert response.status_code == 422
