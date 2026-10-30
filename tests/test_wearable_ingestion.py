from datetime import datetime, timedelta, timezone

from app.db import models as orm


def _provision(client, bracelet_id="BR-0001"):
    response = client.post(f"/api/v1/wearables/devices/{bracelet_id}")
    assert response.status_code == 201, response.text
    return response.json()


def _payload(**overrides):
    payload = {
        "schema_version": "wai.v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "heart_rate_bpm": 82.0,
        "hrv_ms": 46.5,
        "skin_temperature_c": 33.2,
        "movement_activity_score": 28.0,
        "idempotency_key": "wai-test-0001",
    }
    payload.update(overrides)
    return payload


def _ingest(client, provisioned, payload=None, secret=None):
    return client.post(
        f"/api/v1/wearables/edge/{provisioned['device_id']}",
        json=payload or _payload(),
        headers={"X-Wearable-Device-Secret": secret or provisioned["device_secret"]},
    )


def test_wearable_provision_returns_one_time_secret_and_stores_only_digest(client, db_session_factory, seeded):
    provisioned = _provision(client)
    assert provisioned["device_secret"]
    assert provisioned["secret_delivery"] == "shown_once_store_in_device_secret_store"
    with db_session_factory() as db:
        device = db.get(orm.WearableEdgeDevice, provisioned["device_id"])
        assert device is not None
        assert device.secret_hash != provisioned["device_secret"]
        assert len(device.secret_hash) == 64
    assert client.post("/api/v1/wearables/devices/BR-0001").status_code == 409


def test_wearable_ingestion_is_authenticated_persistent_and_idempotent(client, db_session_factory, seeded):
    provisioned = _provision(client)
    payload = _payload(battery_level=91, idempotency_key="wai-idem-0001")
    first = _ingest(client, provisioned, payload)
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["heart_rate_bpm"] == 82.0
    assert body["eda_us"] is None
    assert body["battery_level"] == 91
    assert body["data_status"] == "live_unverified"
    assert body["validation_status"] == "accepted"

    second = _ingest(client, provisioned, payload)
    assert second.status_code == 201
    assert second.json()["id"] == body["id"]

    history = client.get("/api/v1/wearables/BR-0001/observations")
    assert history.status_code == 200
    assert history.json()["count"] == 1
    with db_session_factory() as db:
        bracelet = db.get(orm.Bracelet, "BR-0001")
        assert bracelet.battery_level == 91
        assert db.query(orm.GovernanceAuditEvent).filter_by(
            event_type="wearable.observation_ingested"
        ).count() == 1


def test_wearable_ingestion_rejects_missing_or_wrong_secret(client, seeded):
    provisioned = _provision(client)
    missing = client.post(
        f"/api/v1/wearables/edge/{provisioned['device_id']}", json=_payload()
    )
    assert missing.status_code == 401
    assert _ingest(client, provisioned, secret="wrong-secret").status_code == 401


def test_wearable_ingestion_rejects_stale_timestamp_and_unknown_schema(client, seeded):
    provisioned = _provision(client)
    stale = _payload(observed_at=(datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat())
    assert _ingest(client, provisioned, stale).status_code == 422
    unknown = _payload(schema_version="wai.v99", idempotency_key="wai-schema-0001")
    assert _ingest(client, provisioned, unknown).status_code == 422


def test_wearable_ingestion_requires_at_least_one_measurement(client, seeded):
    provisioned = _provision(client)
    payload = _payload(
        heart_rate_bpm=None, hrv_ms=None, skin_temperature_c=None,
        movement_activity_score=None, eda_us=None, battery_level=88,
    )
    assert _ingest(client, provisioned, payload).status_code == 422


def test_revoked_wearable_device_is_rejected_and_can_be_reprovisioned(client, seeded):
    provisioned = _provision(client)
    revoked = client.post(
        f"/api/v1/wearables/devices/{provisioned['device_id']}/revoke"
    )
    assert revoked.status_code == 200
    assert revoked.json()["is_active"] is False
    assert _ingest(client, provisioned).status_code == 401

    rotated = _provision(client)
    assert rotated["device_id"] == provisioned["device_id"]
    assert rotated["device_secret"] != provisioned["device_secret"]
    assert _ingest(client, rotated).status_code == 201


def test_wearable_provisioning_cannot_cross_school_boundary(client, db_session_factory, seeded):
    with db_session_factory() as db:
        db.add(orm.School(school_id="school-other", name="Other School"))
        db.flush()
        db.add(orm.Student(
            student_id="STU-WEARABLE-OTHER", school_id="school-other",
            name="Other Student", grade="Grade 8", class_section="8A",
            parent_id="P-OTHER", photo_initial="O", is_active=True,
        ))
        db.flush()
        db.add(orm.Bracelet(
            bracelet_id="BR-OTHER-WAI", student_id="STU-WEARABLE-OTHER",
            mac_address="AA:BB:CC:DD:EE:98", battery_level=100,
            is_active=True, firmware_version="1.0.0", notes="",
        ))
        db.commit()
    assert client.post(
        "/api/v1/wearables/devices/BR-OTHER-WAI"
    ).status_code == 404
