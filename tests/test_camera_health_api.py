from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.security import create_access_token, hash_password
from app.db.models import CameraHealthSnapshot, GovernanceAuditEvent, School, User
from app.main import app
from app.services.camera_ingestion import CameraSource, ingestion_service


def _payload(key="camera-health-0001", **overrides):
    value = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "last_seen_age_seconds": 1,
        "fps": 24,
        "latency_ms": 80,
        "consecutive_missed_heartbeats": 0,
        "reconnect_count": 0,
        "frozen_frame": False,
        "idempotency_key": key,
    }
    value.update(overrides)
    return value


def _other_school_client(db_session_factory):
    with db_session_factory() as db:
        db.add(School(school_id="school-health-other", name="Other School"))
        db.flush()
        db.add(User(
            username="health-other-principal",
            full_name="Other Principal",
            hashed_password=hash_password("test-password"),
            role="principal",
            school_id="school-health-other",
            is_active=True,
        ))
        db.commit()
    token = create_access_token("health-other-principal", "health-other-principal")
    return TestClient(app, headers={"Authorization": f"Bearer {token}"})


def test_camera_health_requires_principal(anon_client, auth_headers):
    assert anon_client.post("/api/v1/camera-health/cam-01", json=_payload()).status_code == 401
    response = TestClient(app, headers=auth_headers("teacher")).post(
        "/api/v1/camera-health/cam-01", json=_payload()
    )
    assert response.status_code == 403


def test_camera_health_is_classified_persisted_and_audited(client, db_session_factory, monkeypatch):
    monkeypatch.setattr(ingestion_service, "list_sources", lambda: [
        CameraSource(
            camera_id="cam-01", zone_id="zone-main-gate", label="Gate",
            source_url="synthetic://camera", anonymize_faces=True, school_id="school-primary",
        )
    ])
    response = client.post("/api/v1/camera-health/cam-01", json=_payload())
    assert response.status_code == 201
    assert response.json()["status"] == "online"
    assert response.json()["source"] == "principal_reported"

    duplicate = client.post("/api/v1/camera-health/cam-01", json=_payload())
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == response.json()["id"]

    with db_session_factory() as db:
        assert db.query(CameraHealthSnapshot).count() == 1
        assert db.query(GovernanceAuditEvent).filter_by(
            event_type="camera_health.snapshot_recorded"
        ).count() == 1


def test_camera_health_rejects_unregistered_or_cross_school_camera(client, monkeypatch):
    monkeypatch.setattr(ingestion_service, "list_sources", lambda: [
        CameraSource(
            camera_id="cam-foreign", zone_id="zone-other", label="Foreign",
            source_url="synthetic://camera", anonymize_faces=True, school_id="school-other",
        )
    ])
    response = client.post("/api/v1/camera-health/cam-foreign", json=_payload())
    assert response.status_code == 404


def test_camera_health_history_is_school_scoped(client, db_session_factory, monkeypatch):
    monkeypatch.setattr(ingestion_service, "list_sources", lambda: [
        CameraSource(
            camera_id="cam-01", zone_id="zone-main-gate", label="Gate",
            source_url="synthetic://camera", anonymize_faces=True, school_id="school-primary",
        )
    ])
    created = client.post("/api/v1/camera-health/cam-01", json=_payload())
    assert created.status_code == 201

    other = _other_school_client(db_session_factory)
    response = other.get("/api/v1/camera-health/cam-01")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_camera_health_rejects_unknown_fields_and_non_finite_metrics(client):
    assert client.post(
        "/api/v1/camera-health/cam-01",
        json={**_payload(), "image_base64": "not-accepted"},
    ).status_code == 422
    assert client.post(
        "/api/v1/camera-health/cam-01",
        json=_payload(fps="NaN"),
    ).status_code == 422
