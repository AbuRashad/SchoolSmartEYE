from datetime import datetime, timezone

import pytest

from app.db import models as orm
from app.services import seed_data
from app.services.wearable_aggregation import school_wearable_reporting_metrics


@pytest.fixture()
def seeded(db_session_factory):
    seed_data.populate()
    return db_session_factory


def _add_reporting_devices(db_session_factory, count: int) -> None:
    now = datetime.now(timezone.utc)
    with db_session_factory() as db:
        principal = db.query(orm.User).filter_by(role="principal").first()
        students = db.query(orm.Student).filter_by(school_id="school-primary").order_by(
            orm.Student.student_id
        ).limit(count).all()
        for index, student in enumerate(students):
            bracelet = db.query(orm.Bracelet).filter_by(student_id=student.student_id).first()
            if bracelet is None:
                bracelet = orm.Bracelet(
                    bracelet_id=f"BR-AGG-{index:02d}", student_id=student.student_id,
                    mac_address=f"AA:BB:CC:DD:EF:{index:02X}", battery_level=95,
                    is_active=True, firmware_version="wai-test", notes="",
                )
                db.add(bracelet)
                db.flush()
            device = orm.WearableEdgeDevice(
                device_id=f"WAI-DEVICE-{index:02d}", school_id="school-primary",
                bracelet_id=bracelet.bracelet_id, secret_hash="a" * 64,
                is_active=True, provisioned_by_user_id=principal.id,
            )
            db.add(device)
            db.flush()
            db.add(orm.WearableObservation(
                school_id="school-primary", student_id=student.student_id,
                bracelet_id=bracelet.bracelet_id, device_id=device.device_id,
                observed_at=now, schema_version="wai.v1",
                heart_rate_bpm=80.0, hrv_ms=40.0,
                movement_activity_score=20.0, idempotency_key=f"agg-key-{index:02d}",
                data_status="live_unverified", validation_status="accepted",
            ))
        db.commit()


def test_wearable_aggregation_exposes_only_school_level_coverage(db_session_factory, seeded):
    _add_reporting_devices(db_session_factory, 10)
    with db_session_factory() as db:
        metrics = school_wearable_reporting_metrics(db, "school-primary")
    assert metrics == {
        "wearable_coverage_percent": 100.0,
        "wearable_reporting_devices": 10,
    }
    assert not any("heart" in key or "hrv" in key or "temperature" in key for key in metrics)


def test_wearable_aggregation_suppresses_cohorts_smaller_than_ten(db_session_factory, seeded):
    _add_reporting_devices(db_session_factory, 5)
    with db_session_factory() as db:
        metrics = school_wearable_reporting_metrics(db, "school-primary")
    assert metrics == {}


def test_wearable_aggregation_is_school_scoped(db_session_factory, seeded):
    _add_reporting_devices(db_session_factory, 10)
    with db_session_factory() as db:
        assert school_wearable_reporting_metrics(db, "school-other") == {}


def test_six_agent_orchestrator_receives_only_wearable_coverage(client, db_session_factory, seeded):
    _add_reporting_devices(db_session_factory, 10)
    response = client.post(
        "/api/v1/agent/orchestrate",
        json={"task": "Review school-wide intelligence and data coverage"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    wearable_evidence = [
        item for item in body["evidence"]
        if item["description"] == "Aggregate metric: wearable_coverage_percent"
    ]
    assert wearable_evidence
    assert wearable_evidence[0]["value"] == 100.0
    assert all("heart_rate" not in item["description"] for item in body["evidence"])
    assert "no individual measurements" in body["report"]["data_notice"]
    assert body["requires_human_review"] is True
    assert body["autonomous_action_taken"] is False
