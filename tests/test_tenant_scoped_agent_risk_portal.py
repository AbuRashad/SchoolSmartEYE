"""Negative tests for school scoping in agent, attendance-risk, and portal APIs."""
from datetime import date, timedelta

from app.db import models as orm
from app.services import attendance_risk, seed_data, ssi_history
import pytest

API = "/api/v1"


@pytest.fixture
def seeded():
    seed_data.populate()


def _add_other_school(db):
    db.add(orm.School(school_id="OTHER-SCHOOL", name="Other School", is_active=True))
    db.add(orm.Student(
        student_id="OTHER-STUDENT-001",
        school_id="OTHER-SCHOOL",
        name="Other School Student",
        grade="Grade 8",
        class_section="8A",
        parent_id="OTHER-PARENT",
        photo_initial="O",
        is_active=True,
    ))
    for offset in range(8):
        db.add(orm.AttendanceRecord(
            student_id="OTHER-STUDENT-001",
            date=date.today() - timedelta(days=offset),
            status="absent",
        ))
    db.commit()


def test_attendance_risk_never_mixes_school_records(client, seeded, db_session_factory):
    with db_session_factory() as db:
        _add_other_school(db)
        scoped = attendance_risk.school_risk(db, "DEMO-SCHOOL-001", 14)
        assert all(row["student_id"] != "OTHER-STUDENT-001" for row in scoped)

    response = client.get(f"{API}/risk/attendance")
    assert response.status_code == 200
    ids = {row["student_id"] for row in response.json()["students"]}
    assert "OTHER-STUDENT-001" not in ids
    assert len(ids) == 10


def test_guessed_cross_school_student_is_not_visible_to_risk_or_agent(
    client, seeded, db_session_factory
):
    with db_session_factory() as db:
        _add_other_school(db)

    risk = client.get(f"{API}/risk/attendance/OTHER-STUDENT-001")
    recommendation = client.get(f"{API}/agent/recommendations/OTHER-STUDENT-001")
    feedback = client.post(
        f"{API}/agent/feedback",
        json={
            "session_id": "CROSS-SCHOOL-SESSION",
            "student_id": "OTHER-STUDENT-001",
            "predicted_state": "distracted",
            "confirmed_state": "engaged",
        },
    )
    assert risk.status_code == 404
    assert recommendation.status_code == 404
    assert feedback.status_code == 404


def test_school_query_parameter_is_membership_checked(client, seeded):
    response = client.get(f"{API}/risk/attendance", params={"school_id": "OTHER-SCHOOL"})
    assert response.status_code == 404


def test_student_portal_does_not_return_mock_or_unlinked_student_data(client):
    response = client.get(f"{API}/portal/student")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["status"] == "identity_link_required"
    assert body["student"] is None
    assert body["school_id"] == "DEMO-SCHOOL-001"
    assert "name" not in body
    assert "student_id" not in body


def test_student_crud_is_school_scoped_and_assigns_authenticated_school(
    client, seeded, db_session_factory
):
    with db_session_factory() as db:
        _add_other_school(db)

    listed = client.get(f"{API}/students")
    assert listed.status_code == 200
    listed_ids = {row["student_id"] for row in listed.json()}
    assert "OTHER-STUDENT-001" not in listed_ids

    guessed_profile = client.get(f"{API}/students/OTHER-STUDENT-001/profile")
    guessed_history = client.get(f"{API}/students/OTHER-STUDENT-001/behavioral-history")
    guessed_update = client.patch(
        f"{API}/students/OTHER-STUDENT-001",
        json={"name": "Tampered"},
    )
    guessed_delete = client.delete(f"{API}/students/OTHER-STUDENT-001")
    assert guessed_profile.status_code == 404
    assert guessed_history.status_code == 404
    assert guessed_update.status_code == 404
    assert guessed_delete.status_code == 404


def test_new_student_is_assigned_to_server_resolved_school(
    client, seeded, db_session_factory
):
    response = client.post(
        f"{API}/students",
        json={
            "student_id": "NEW-TENANT-STUDENT",
            "name": "New Student",
            "grade": "Grade 7",
            "class_section": "7A",
            "parent_id": "NEW-PARENT",
        },
    )
    assert response.status_code == 201
    with db_session_factory() as db:
        student = db.get(orm.Student, "NEW-TENANT-STUDENT")
        assert student is not None
        assert student.school_id == "DEMO-SCHOOL-001"


def test_zones_endpoint_returns_only_authenticated_school_zones(client, seeded, db_session_factory):
    with db_session_factory() as db:
        db.add(orm.School(school_id="OTHER-SCHOOL", name="Other School", is_active=True))
        db.add(orm.Zone(zone_id="OTHER-ZONE-001", school_id="OTHER-SCHOOL", label="Other Zone", zone_type="entrance", capacity=10, floor=0, grid_x=0, grid_y=0))
        db.commit()
    response = client.get(f"{API}/zones")
    assert response.status_code == 200
    assert len(response.json()) == 12
    assert "OTHER-ZONE-001" not in {row["zone_id"] for row in response.json()}


def test_bracelet_endpoints_follow_the_owning_students_school(
    client, seeded, db_session_factory
):
    with db_session_factory() as db:
        _add_other_school(db)
        db.add(orm.Bracelet(
            bracelet_id="OTHER-BRACELET-001",
            student_id="OTHER-STUDENT-001",
            mac_address="AA:BB:CC:DD:EE:99",
            battery_level=80,
            is_active=True,
            firmware_version="1.0.0",
            notes="",
        ))
        db.commit()

    listed = client.get(f"{API}/bracelets")
    assert listed.status_code == 200
    assert "OTHER-BRACELET-001" not in {row["bracelet_id"] for row in listed.json()}

    guessed_update = client.patch(
        f"{API}/bracelets/OTHER-BRACELET-001",
        json={"notes": "unauthorized"},
    )
    guessed_delete = client.delete(f"{API}/bracelets/OTHER-BRACELET-001")
    cross_school_assignment = client.post(
        f"{API}/bracelets",
        json={
            "bracelet_id": "CROSS-SCHOOL-BRACELET",
            "student_id": "OTHER-STUDENT-001",
            "mac_address": "AA:BB:CC:DD:EE:98",
        },
    )
    assert guessed_update.status_code == 404
    assert guessed_delete.status_code == 404
    assert cross_school_assignment.status_code == 400


def test_camera_and_zone_dependent_services_fail_closed(client, seeded):
    camera_list = client.get(f"{API}/cameras")
    assert camera_list.status_code == 200
    for path in (
        f"{API}/analytics/overview",
        f"{API}/dashboard/summary",
        f"{API}/dashboard/alerts",
        f"{API}/dashboard/heatmap",
        f"{API}/dashboard/live",
    ):
        response = client.get(path)
        assert response.status_code == 503, f"{path} returned {response.status_code}"


def test_global_operational_feeds_fail_closed_until_school_partitioned(client, seeded):
    for path in (
        f"{API}/ssi/live",
        f"{API}/ssi/history",
        f"{API}/units/capture/health",
        f"{API}/units/alerts/summary",
        f"{API}/settings",
    ):
        response = client.get(path)
        assert response.status_code == 503, f"{path} returned {response.status_code}"



def test_camera_registration_requires_zone_from_authenticated_school(
    client, seeded, db_session_factory
):
    with db_session_factory() as db:
        db.add(orm.School(school_id="OTHER-SCHOOL", name="Other School", is_active=True))
        db.add(orm.Zone(
            zone_id="OTHER-ZONE-001",
            school_id="OTHER-SCHOOL",
            label="Other Campus Gate",
            zone_type="entrance",
            capacity=20,
            floor=0,
            grid_x=0,
            grid_y=0,
        ))
        db.add(orm.Camera(
            camera_id="OTHER-CAMERA-001",
            zone_id="OTHER-ZONE-001",
            label="Other Campus Camera",
            is_active=True,
        ))
        db.commit()

    denied_create = client.post(
        f"{API}/cameras",
        json={
            "camera_id": "CROSS-TENANT-CAMERA",
            "zone_id": "OTHER-ZONE-001",
            "label": "Intruder Camera",
            "source_url": "0",
        },
    )
    denied_start = client.post(f"{API}/cameras/OTHER-CAMERA-001/start")
    denied_stop = client.post(f"{API}/cameras/OTHER-CAMERA-001/stop")
    denied_delete = client.delete(f"{API}/cameras/OTHER-CAMERA-001")
    denied_snapshot = client.get(f"{API}/cameras/OTHER-CAMERA-001/snapshot.jpg")
    denied_stream = client.get(f"{API}/cameras/OTHER-CAMERA-001/stream.mjpg")
    assert denied_create.status_code == 404
    assert denied_start.status_code == 404
    assert denied_stop.status_code == 404
    assert denied_delete.status_code == 404
    assert denied_snapshot.status_code == 404
    assert denied_stream.status_code == 404



def test_ssi_history_and_polling_are_isolated_by_school(client, seeded, db_session_factory):
    from datetime import datetime, timezone

    with db_session_factory() as db:
        db.add(orm.School(school_id="OTHER-SCHOOL", name="Other School", is_active=True))
        db.commit()
        ssi_history.record_snapshot(
            db, "OTHER-SCHOOL", 12.5, source="test",
            recorded_at=datetime.now(timezone.utc),
        )
        demo = ssi_history.summarize(db, "DEMO-SCHOOL-001", 365)
        other = ssi_history.summarize(db, "OTHER-SCHOOL", 365)
        assert demo["snapshots"] == 30
        assert other["snapshots"] == 1
        assert other["average"] == 12.5
        assert ssi_history.record_if_due(
            db, "OTHER-SCHOOL", 99.0, source="test", min_interval_seconds=300
        ) is False
        assert ssi_history.record_if_due(
            db, "DEMO-SCHOOL-001", 99.0, source="test", min_interval_seconds=300
        ) is True

    response = client.get(f"{API}/ssi/history")
    assert response.status_code == 200
    assert response.json()["snapshots"] == 31
    assert response.json()["average"] != 12.5
