from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import CameraEdgeDevice, CameraHealthSnapshot, User
from app.main import app


def _insert_edge_camera(db_session_factory, *, school_id="school-primary", camera_id="cam-1"):
    now = datetime.now(timezone.utc)
    with db_session_factory() as db:
        principal = db.scalar(select(User).where(User.role == "principal", User.school_id == school_id))
        device = CameraEdgeDevice(
            device_id=f"device-{school_id}-{camera_id}",
            school_id=school_id,
            camera_id=camera_id,
            secret_hash="a" * 64,
            is_active=True,
            provisioned_by_user_id=principal.id,
            last_seen_at=now,
        )
        db.add(device)
        db.flush()
        db.add(CameraHealthSnapshot(
            school_id=school_id,
            camera_id=camera_id,
            status="online",
            observed_at=now,
            last_seen_at=now,
            fps=24,
            latency_ms=50,
            consecutive_missed_heartbeats=0,
            reconnect_count=0,
            frozen_frame=False,
            idempotency_key=f"edge-{school_id}-{camera_id}",
            source="edge_agent",
            created_by_user_id=principal.id,
        ))
        db.commit()


def test_analytics_uses_only_authenticated_edge_camera_telemetry(auth_headers, db_session_factory):
    _insert_edge_camera(db_session_factory)
    client = TestClient(app, headers=auth_headers("principal"))
    payload = client.get("/api/v1/analytics/overview").json()

    assert payload["data_status"] == "partial"
    assert payload["active_cameras"] == 1
    assert payload["total_units"] == 1
    assert payload["uptime_percent"] == 100.0
    assert payload["attendance_rate"] is None
    assert payload["metrics"]["active_cameras"]["source"] == "authenticated_edge_agent_telemetry"


def test_principal_camera_analytics_is_tenant_scoped(auth_headers, db_session_factory):
    from app.db.models import School

    with db_session_factory() as db:
        db.add(School(school_id="school-other", name="Other School"))
        db.commit()
    _insert_edge_camera(db_session_factory, camera_id="cam-primary")
    _insert_edge_camera(db_session_factory, school_id="school-other", camera_id="cam-other")

    principal_client = TestClient(app, headers=auth_headers("principal"))
    ministry_client = TestClient(app, headers=auth_headers("ministry"))

    principal_payload = principal_client.get("/api/v1/analytics/overview").json()
    ministry_payload = ministry_client.get("/api/v1/analytics/overview").json()

    assert principal_payload["total_units"] == 1
    assert ministry_payload["total_units"] == 2
    assert ministry_payload["active_cameras"] == 2
    assert "school-primary" not in str(ministry_payload)
    assert "school-other" not in str(ministry_payload)


def test_principal_reported_snapshots_are_not_live_analytics(auth_headers, db_session_factory):
    from app.db.models import User

    now = datetime.now(timezone.utc)
    with db_session_factory() as db:
        principal = db.scalar(select(User).where(User.role == "principal"))
        db.add(CameraEdgeDevice(
            device_id="device-no-edge",
            school_id="school-primary",
            camera_id="cam-manual",
            secret_hash="b" * 64,
            is_active=True,
            provisioned_by_user_id=principal.id,
            last_seen_at=now,
        ))
        db.add(CameraHealthSnapshot(
            school_id="school-primary",
            camera_id="cam-manual",
            status="online",
            observed_at=now,
            last_seen_at=now,
            fps=24,
            latency_ms=50,
            consecutive_missed_heartbeats=0,
            reconnect_count=0,
            frozen_frame=False,
            idempotency_key="manual-report-only",
            source="principal_reported",
            created_by_user_id=principal.id,
        ))
        db.commit()

    client = TestClient(app, headers=auth_headers("principal"))
    payload = client.get("/api/v1/analytics/overview").json()
    assert payload["data_status"] == "unavailable"
    assert payload["active_cameras"] is None
    assert payload["uptime_percent"] is None
