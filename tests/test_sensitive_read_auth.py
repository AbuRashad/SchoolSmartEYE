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


def test_authenticated_analytics_and_dashboard_return_school_scoped_views(client: TestClient):
    for path in (
        "/api/v1/analytics/overview",
        "/api/v1/dashboard/summary",
        "/api/v1/dashboard/alerts",
        "/api/v1/dashboard/heatmap",
        "/api/v1/dashboard/live",
    ):
        response = client.get(path)
        assert response.status_code == 200, f"{path} returned {response.status_code}"
        body = response.json()
        if isinstance(body, dict) and "school_id" in body:
            assert body["school_id"] == "DEMO-SCHOOL-001"
        if isinstance(body, dict) and "schoolId" in body:
            assert body["schoolId"] == "DEMO-SCHOOL-001"


def test_student_portal_and_agent_remain_available_when_properly_scoped(client: TestClient):
    for path in (
        "/api/v1/portal/student",
        "/api/v1/agent/insights",
    ):
        response = client.get(path)
        assert response.status_code == 200, f"{path} returned {response.status_code}"


def test_reports_fail_closed_until_school_scoped(client: TestClient):
    for path in ("/api/v1/reports/list", "/api/v1/reports/stats"):
        response = client.get(path)
        assert response.status_code == 403  # teacher role is not Ministry
