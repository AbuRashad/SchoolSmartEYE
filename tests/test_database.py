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
        db.add(orm.Student(student_id="X1", school_id="school-primary", name="Only", grade="G1", class_section="A", parent_id="P"))
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


def test_school_metrics_come_from_database(db_session_factory) -> None:
    with db_session_factory() as db:
        seed_data.seed_database(db)
        metrics = seed_data.get_school_metrics(db)
    assert metrics.total_students == 10
    assert metrics.present_today == 9  # one student is LATE
