from datetime import datetime, timezone

from app.db.models import CameraEdgeDevice, CameraHealthSnapshot, GovernanceAuditEvent
from app.services.camera_ingestion import CameraSource, ingestion_service


def _source(monkeypatch, school_id="school-primary", camera_id="cam-edge-01"):
    monkeypatch.setattr(ingestion_service, "list_sources", lambda: [
        CameraSource(
            camera_id=camera_id, zone_id="zone-main-gate", label="Edge Camera",
            source_url="synthetic://camera", anonymize_faces=True, school_id=school_id,
        )
    ])


def _heartbeat(key="edge-heartbeat-001"):
    return {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "last_seen_age_seconds": 1,
        "fps": 24,
        "latency_ms": 75,
        "consecutive_missed_heartbeats": 0,
        "reconnect_count": 0,
        "frozen_frame": False,
        "idempotency_key": key,
    }


def _provision(client, monkeypatch):
    _source(monkeypatch)
    response = client.post("/api/v1/camera-health/devices/cam-edge-01")
    assert response.status_code == 201
    return response.json()


def test_edge_device_provisioning_returns_secret_once_and_stores_only_digest(client, db_session_factory, monkeypatch):
    provisioned = _provision(client, monkeypatch)
    assert provisioned["device_secret"]
    with db_session_factory() as db:
        device = db.get(CameraEdgeDevice, provisioned["device_id"])
        assert device is not None
        assert device.secret_hash != provisioned["device_secret"]
        assert len(device.secret_hash) == 64
    duplicate = client.post("/api/v1/camera-health/devices/cam-edge-01")
    assert duplicate.status_code == 409


def test_edge_heartbeat_authenticates_persists_and_is_idempotent(client, db_session_factory, monkeypatch):
    provisioned = _provision(client, monkeypatch)
    url = f"/api/v1/camera-health/edge/{provisioned['device_id']}"
    headers = {"X-Edge-Device-Secret": provisioned["device_secret"]}
    first = client.post(url, json=_heartbeat(), headers=headers)
    assert first.status_code == 201
    assert first.json()["source"] == "edge_agent"
    second = client.post(url, json=_heartbeat(), headers=headers)
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    with db_session_factory() as db:
        assert db.query(CameraHealthSnapshot).filter_by(source="edge_agent").count() == 1
        assert db.query(GovernanceAuditEvent).filter_by(event_type="camera_edge.heartbeat_recorded").count() == 1


def test_edge_heartbeat_rejects_bad_secret_and_revoked_device(client, monkeypatch):
    provisioned = _provision(client, monkeypatch)
    url = f"/api/v1/camera-health/edge/{provisioned['device_id']}"
    assert client.post(url, json=_heartbeat(), headers={"X-Edge-Device-Secret": "wrong"}).status_code == 401
    revoke = client.post(f"/api/v1/camera-health/devices/{provisioned['device_id']}/revoke")
    assert revoke.status_code == 200
    assert client.post(url, json=_heartbeat(), headers={"X-Edge-Device-Secret": provisioned["device_secret"]}).status_code == 401


def test_edge_heartbeat_rejects_missing_credentials(client, monkeypatch):
    provisioned = _provision(client, monkeypatch)
    response = client.post(f"/api/v1/camera-health/edge/{provisioned['device_id']}", json=_heartbeat())
    assert response.status_code == 401


def test_edge_device_cannot_be_provisioned_for_unregistered_camera(client, monkeypatch):
    monkeypatch.setattr(ingestion_service, "list_sources", lambda: [])
    assert client.post("/api/v1/camera-health/devices/unknown").status_code == 404



def test_edge_heartbeat_accepts_maximum_length_idempotency_key(client, monkeypatch):
    provisioned = _provision(client, monkeypatch)
    payload = _heartbeat(key="k" * 128)
    response = client.post(
        f"/api/v1/camera-health/edge/{provisioned['device_id']}",
        json=payload,
        headers={"X-Edge-Device-Secret": provisioned["device_secret"]},
    )
    assert response.status_code == 201
    assert response.json()["source"] == "edge_agent"


def test_edge_heartbeat_rejects_stale_device_clock(client, monkeypatch):
    from datetime import timedelta

    provisioned = _provision(client, monkeypatch)
    payload = _heartbeat()
    payload["observed_at"] = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    response = client.post(
        f"/api/v1/camera-health/edge/{provisioned['device_id']}",
        json=payload,
        headers={"X-Edge-Device-Secret": provisioned["device_secret"]},
    )
    assert response.status_code == 422
