"""Negative tests for school scoping in agent, attendance-risk, and portal APIs."""
from datetime import date, timedelta

from app.db import models as orm
from app.services import attendance_risk

API = "/api/v1"


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
