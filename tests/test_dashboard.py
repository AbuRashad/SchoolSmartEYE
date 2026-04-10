from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_dashboard_summary_contract() -> None:
    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["schoolName"] == "Smart School Safety System"
    assert 0 <= payload["ssi"] <= 100
    assert payload["benchmark"] == 75
    assert payload["websocketStatus"] == "connected"


def test_dashboard_alerts_contract() -> None:
    response = client.get("/api/v1/dashboard/alerts")

    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) >= 2
    assert any(alert["severity"] == "critical" and alert["title"] == "Coherence Rupture" for alert in alerts)
    assert any(alert["severity"] == "warning" and alert["title"] == "Anomaly Coefficient" for alert in alerts)


def test_dashboard_heatmap_contract() -> None:
    response = client.get("/api/v1/dashboard/heatmap")

    assert response.status_code == 200
    payload = response.json()

    assert payload["location_id"] == "main-campus"
    assert payload["availableTimeSlots"] == ["live", "prediction_15m"]
    assert len(payload["cells"]) == 8

    sample = payload["cells"][0]
    assert {"x", "y", "time_slot", "risk_intensity", "reason", "label"}.issubset(sample.keys())
    assert 0.0 <= sample["risk_intensity"] <= 1.0


def test_dashboard_websocket_initial_snapshot_and_refresh() -> None:
    with client.websocket_connect("/api/v1/dashboard/ws") as websocket:
        initial = websocket.receive_json()
        assert initial["schoolName"] == "Smart School Safety System"
        assert initial["fetchedFromBackend"] is True

        websocket.send_text("refresh")
        refreshed = websocket.receive_json()
        assert refreshed["availableTimeSlots"] == ["live", "prediction_15m"]
        assert len(refreshed["liveAlerts"]) >= 2
