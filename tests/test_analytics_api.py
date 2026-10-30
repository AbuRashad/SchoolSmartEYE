from fastapi.testclient import TestClient

from app.main import app


def test_analytics_overview_never_labels_seed_metrics_as_live(auth_headers):
    client = TestClient(app, headers=auth_headers("principal"))
    response = client.get("/api/v1/analytics/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_status"] == "unavailable"
    assert "seed" in payload["data_notice"].lower()
    assert payload["attendance_rate"] is None
    assert payload["total_students"] is None
    assert payload["active_cameras"] is None
    assert payload["incidents_today"] is None
    assert payload["compliance_score"] is None
    assert all(metric["status"] == "unavailable" for metric in payload["metrics"].values())
    assert all(metric["value"] is None for metric in payload["metrics"].values())


def test_analytics_overview_requires_authentication():
    client = TestClient(app)
    response = client.get("/api/v1/analytics/overview")
    assert response.status_code == 401
