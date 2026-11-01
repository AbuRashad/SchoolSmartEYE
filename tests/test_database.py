from sqlalchemy import func, select

from app.db import models as orm
from app.services import seed_data


def test_seed_inserts_demo_data_only_when_tables_empty(db_session_factory) -> None:
    with db_session_factory() as db:
        assert seed_data.seed_database(db) is True
        students = db.scalar(select(func.count()).select_from(orm.Student))
        bracelets = db.scalar(select(func.count()).select_from(orm.Bracelet))
        attendance = db.scalar(select(func.count()).select_from(orm.AttendanceRecord))
        notifications = db.scalar(select(func.count()).select_from(orm.Notification))
        assert (students, bracelets, notifications) == (10, 5, 4)
        assert attendance == 10 + 70

        # Second call must not duplicate anything
        assert seed_data.seed_database(db) is False
        assert db.scalar(select(func.count()).select_from(orm.Student)) == 10


def test_seed_does_not_overwrite_existing_data(db_session_factory) -> None:
    with db_session_factory() as db:
        db.add(orm.Student(student_id="X1", name="Only", grade="G1", class_section="A", parent_id="P"))
        db.commit()
        assert seed_data.seed_database(db) is False
        assert db.scalar(select(func.count()).select_from(orm.Student)) == 1


def test_students_persist_across_sessions(client, db_session_factory) -> None:
    r = client.post(
        "/api/v1/students",
        json={"student_id": "S-1", "name": "Zed", "grade": "G9", "class_section": "A", "parent_id": "P-1"},
    )
    assert r.status_code == 201
    assert r.json()["photo_initial"] == "Z"
    with db_session_factory() as db:
        assert db.get(orm.Student, "S-1").name == "Zed"
    assert [s["student_id"] for s in client.get("/api/v1/students").json()] == ["S-1"]


def test_delete_student_cascades_to_bracelet_and_attendance(client, db_session_factory) -> None:
    with db_session_factory() as db:
        seed_data.seed_database(db)
    sid = "STU-2024-0847"
    assert client.delete(f"/api/v1/students/{sid}").status_code == 204
    with db_session_factory() as db:
        assert db.get(orm.Student, sid) is None
        assert db.scalar(select(func.count()).select_from(orm.Bracelet).where(orm.Bracelet.student_id == sid)) == 0
        assert db.scalar(
            select(func.count()).select_from(orm.AttendanceRecord).where(orm.AttendanceRecord.student_id == sid)
        ) == 0


def test_datetimes_round_trip_as_utc(db_session_factory) -> None:
    with db_session_factory() as db:
        seed_data.seed_database(db)
        b = db.get(orm.Bracelet, "BR-0001")
        assert b.last_seen_at.tzinfo is not None
        assert b.last_seen_at.utcoffset().total_seconds() == 0


def test_school_metrics_are_scoped_to_the_requested_school(db_session_factory) -> None:
    from datetime import date

    with db_session_factory() as db:
        seed_data.seed_database(db)
        db.add(orm.School(school_id="OTHER-METRICS-SCHOOL", name="Other Metrics School", is_active=True))
        db.add(orm.Student(
            student_id="OTHER-METRICS-STUDENT",
            school_id="OTHER-METRICS-SCHOOL",
            name="Other Student",
            grade="Grade 8",
            class_section="8A",
            parent_id="OTHER-METRICS-PARENT",
        ))
        db.add(orm.Zone(
            zone_id="OTHER-METRICS-ZONE",
            school_id="OTHER-METRICS-SCHOOL",
            label="Other Zone",
            zone_type="classroom",
            capacity=20,
            floor=1,
            grid_x=0,
            grid_y=0,
        ))
        db.flush()
        db.add(orm.AttendanceRecord(
            student_id="OTHER-METRICS-STUDENT",
            date=date.today(),
            status="present",
        ))
        db.add(orm.Camera(
            camera_id="OTHER-METRICS-CAMERA",
            zone_id="OTHER-METRICS-ZONE",
            label="Other Camera",
            is_active=True,
        ))
        from datetime import datetime, timezone
        db.add(orm.Incident(
            incident_id="OTHER-METRICS-INCIDENT",
            zone_id="OTHER-METRICS-ZONE",
            severity="high",
            description="Other school's incident",
            detected_at=datetime.now(timezone.utc),
            resolved=False,
        ))
        db.commit()

        demo_metrics = seed_data.get_school_metrics(db, "DEMO-SCHOOL-001")
        other_metrics = seed_data.get_school_metrics(db, "OTHER-METRICS-SCHOOL")

    assert demo_metrics.total_students == 10
    assert demo_metrics.present_today == 9  # one student is LATE
    assert other_metrics.total_students == 1
    assert other_metrics.present_today == 1
    assert other_metrics.attendance_rate == 100.0
    assert other_metrics.active_cameras == 1
    assert other_metrics.open_incidents == 1


def test_school_metrics_reject_missing_school_scope(db_session_factory) -> None:
    import pytest

    with db_session_factory() as db:
        with pytest.raises(ValueError, match="school_id is required"):
            seed_data.get_school_metrics(db, "")
