from fastapi.testclient import TestClient


def test_sensitive_read_endpoints_require_authentication(anon_client: TestClient):
    paths = [
        "/api/v1/analytics/overview",
        "/api/v1/portal/student",
        "/api/v1/agent/insights",
        "/api/v1/agent/baselines",
        "/api/v1/agent/recommendations/STU-2024-0847",
        "/api/v1/dashboard/summary",
        "/api/v1/dashboard/alerts",
        "/api/v1/dashboard/heatmap",
        "/api/v1/dashboard/live",
    ]
    for path in paths:
        response = anon_client.get(path)
        assert response.status_code == 401, f"{path} returned {response.status_code}"


def test_teacher_can_read_protected_dashboard_and_demo_data(client: TestClient):
    for path in (
        "/api/v1/analytics/overview",
        "/api/v1/portal/student",
        "/api/v1/agent/insights",
        "/api/v1/dashboard/summary",
        "/api/v1/dashboard/alerts",
        "/api/v1/dashboard/heatmap",
    ):
        response = client.get(path)
        assert response.status_code == 200, f"{path} returned {response.status_code}"


def test_analytics_overview_identifies_placeholder_metrics(client: TestClient):
    response = client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_status"] == "demo"
    assert "not live school data" in payload["data_notice"]
