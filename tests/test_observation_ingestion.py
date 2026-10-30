from datetime import datetime, timezone

from app.db.models import AggregateObservation


def test_principal_can_ingest_aggregate_observation(client):
    response = client.post("/api/v1/observations", json={
        "metric_key": "attendance_rate",
        "metric_value": 93.5,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source_id": "school-attendance-system",
        "idempotency_key": "attendance-2026-10-30",
    })
    assert response.status_code == 201
    body = response.json()
    assert body["data_status"] == "live_unverified"
    assert body["validation_status"] == "pending"
    assert body["school_id"] == "school-primary"


def test_observation_rejects_client_controlled_status(client):
    response = client.post("/api/v1/observations", json={
        "metric_key": "attendance_rate",
        "metric_value": 93.5,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source_id": "attendance",
        "idempotency_key": "attendance-status-001",
        "data_status": "live_verified",
    })
    assert response.status_code == 422


def test_observation_rejects_unknown_metric(client):
    response = client.post("/api/v1/observations", json={
        "metric_key": "student_name",
        "metric_value": 1,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source_id": "attendance",
        "idempotency_key": "unknown-metric-001",
    })
    assert response.status_code == 422


def test_observation_rejects_duplicate_idempotency_key(client):
    payload = {
        "metric_key": "attendance_rate",
        "metric_value": 91,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source_id": "attendance",
        "idempotency_key": "attendance-duplicate-001",
    }
    assert client.post("/api/v1/observations", json=payload).status_code == 201
    assert client.post("/api/v1/observations", json=payload).status_code == 409


def test_teacher_cannot_ingest_observation(anon_client, auth_headers):
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app, headers=auth_headers("teacher"))
    response = client.post("/api/v1/observations", json={
        "metric_key": "attendance_rate",
        "metric_value": 91,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "source_id": "attendance",
        "idempotency_key": "teacher-forbidden-001",
    })
    assert response.status_code == 403
