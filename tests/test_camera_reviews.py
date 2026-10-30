from datetime import datetime, timezone

from app.db.models import CameraReviewEvent, GovernanceAuditEvent


def _payload(key="camera-event-0001"):
    return {
        "idempotency_key": key,
        "camera_id": "cam-01",
        "zone_id": "zone-main-gate",
        "event_type": "crowd_density_spike",
        "severity": "medium",
        "confidence": 0.82,
        "summary": "Synthetic crowd-density threshold event",
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "evidence_ref": "evidence://synthetic/event-0001",
    }


def test_camera_event_requires_authentication(anon_client):
    response = anon_client.post("/api/v1/camera-reviews", json=_payload())
    assert response.status_code == 401


def test_camera_event_is_persisted_and_idempotent(client, db_session_factory):
    first = client.post("/api/v1/camera-reviews", json=_payload())
    assert first.status_code == 201
    event_id = first.json()["event_id"]
    assert first.json()["status"] == "pending"

    duplicate = client.post("/api/v1/camera-reviews", json=_payload())
    assert duplicate.status_code == 200
    assert duplicate.json()["event_id"] == event_id

    with db_session_factory() as db:
        assert db.query(CameraReviewEvent).count() == 1
        assert db.query(GovernanceAuditEvent).filter_by(
            event_type="camera_review.event_created"
        ).count() == 1


def test_only_principal_can_review_events(anon_client, auth_headers):
    response = anon_client.post(
        "/api/v1/camera-reviews",
        json=_payload(),
        headers=auth_headers("teacher"),
    )
    assert response.status_code == 403


def test_review_decision_is_audited_and_cannot_be_repeated(client, db_session_factory):
    created = client.post("/api/v1/camera-reviews", json=_payload())
    event_id = created.json()["event_id"]

    decision = client.post(
        f"/api/v1/camera-reviews/{event_id}/review",
        json={"decision": "needs_follow_up", "note": "Check the synthetic event manually."},
    )
    assert decision.status_code == 200
    assert decision.json()["status"] == "needs_follow_up"
    assert decision.json()["reviewed_by_user_id"] is not None

    repeated = client.post(
        f"/api/v1/camera-reviews/{event_id}/review",
        json={"decision": "confirmed", "note": "Second decision must be rejected."},
    )
    assert repeated.status_code == 409

    with db_session_factory() as db:
        assert db.query(GovernanceAuditEvent).filter_by(
            event_type="camera_review.decision_recorded"
        ).count() == 1


def test_review_event_is_not_visible_to_another_school(client, db_session_factory):
    from app.db.models import School, User
    from app.core.security import hash_password
    from app.core.security import create_access_token
    from fastapi.testclient import TestClient
    from app.main import app

    created = client.post("/api/v1/camera-reviews", json=_payload())
    with db_session_factory() as db:
        db.add(School(school_id="school-other", name="Other School"))
        db.flush()
        db.add(User(
            username="other-principal",
            full_name="Other Principal",
            hashed_password=hash_password("test-password"),
            role="principal",
            school_id="school-other",
            is_active=True,
        ))
        db.commit()

    token = create_access_token("other-principal", "other-principal")
    other_client = TestClient(app, headers={"Authorization": f"Bearer {token}"})
    listed = other_client.get("/api/v1/camera-reviews")
    assert listed.status_code == 200
    assert listed.json()["items"] == []

    hidden = other_client.post(
        f"/api/v1/camera-reviews/{created.json()['event_id']}/review",
        json={"decision": "dismissed", "note": ""},
    )
    assert hidden.status_code == 404
