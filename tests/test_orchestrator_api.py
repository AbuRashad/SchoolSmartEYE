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


def test_principal_can_call_orchestrator_and_result_requires_review(client: TestClient):
    response = client.post(
        "/api/v1/agent/orchestrate",
        json={"task": "Review aggregate school signals"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "native"
    assert payload["requires_human_review"] is True
    assert payload["autonomous_action_taken"] is False
    assert [stage["name"] for stage in payload["stages"]] == [
        "analytics",
        "safety",
        "academic",
        "operations",
        "evidence",
        "ethics_review",
    ]
    assert payload["status"] == "completed"
    assert payload["report"]["data_status"] == "demo"
    assert payload["report"]["data_notice"] == "These are illustrative demo metrics, not live school data."
    assert any("not live school data" in item for item in payload["report"]["limitations"])


def test_orchestrator_rejects_unknown_request_fields(client: TestClient):
    response = client.post(
        "/api/v1/agent/orchestrate",
        json={"task": "Review aggregate school signals", "student_ids": ["private-id"]},
    )
    assert response.status_code == 422
