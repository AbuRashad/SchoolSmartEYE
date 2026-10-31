from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_rest_endpoints_fail_closed_until_tenant_scoped(client: TestClient) -> None:
    for path in (
        "/api/v1/dashboard/summary",
        "/api/v1/dashboard/alerts",
        "/api/v1/dashboard/heatmap",
        "/api/v1/dashboard/live",
    ):
        response = client.get(path)
        assert response.status_code == 503, f"{path} returned {response.status_code}"
        assert response.json()["detail"]["code"] == "SCHOOL_SCOPED_DASHBOARD_UNAVAILABLE"


def test_dashboard_websocket_is_refused_until_tenant_scoped(auth_headers) -> None:
    token = auth_headers("teacher")["Authorization"].split()[1]
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect(f"/api/v1/dashboard/ws?access_token={token}") as websocket:
            websocket.receive_json()


import pytest
