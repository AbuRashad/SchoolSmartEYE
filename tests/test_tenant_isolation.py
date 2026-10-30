"""School tenant isolation and ministry read-only access for students/bracelets."""
import pytest
from fastapi.testclient import TestClient

from app.core import security
from app.db import models as orm
from app.main import app
from tests.conftest import bearer

SCHOOL_A, SCHOOL_B = "school-a", "school-b"


@pytest.fixture()
def two_schools(db_session_factory):
    with db_session_factory() as db:
        db.add_all([
            orm.School(school_id=SCHOOL_A, name="School A"),
            orm.School(school_id=SCHOOL_B, name="School B"),
        ])
        for username, role, school in [
            ("principal_a", "principal", SCHOOL_A),
            ("teacher_a", "teacher", SCHOOL_A),
            ("principal_b", "principal", SCHOOL_B),
            ("ministry_x", "ministry", None),
        ]:
            db.add(orm.User(
                username=username,
                role=role,
                school_id=school,
                hashed_password=security.hash_password("x"),
            ))
        for student_id, school in [("A-1", SCHOOL_A), ("B-1", SCHOOL_B), ("B-2", SCHOOL_B)]:
            db.add(orm.Student(
                student_id=student_id,
                school_id=school,
                name=student_id,
                grade="5",
                class_section="1",
                parent_id=f"P-{student_id}",
            ))
        db.flush()
        db.add_all([
            orm.Bracelet(bracelet_id="BR-A1", student_id="A-1", mac_address="AA:AA:AA:AA:AA:01"),
            orm.Bracelet(bracelet_id="BR-B1", student_id="B-1", mac_address="AA:AA:AA:AA:AA:02"),
        ])
        db.commit()


def _client(username: str, role: str) -> TestClient:
    token = security.create_access_token(username, role)
    return TestClient(app, headers=bearer(token))


def test_school_users_only_list_their_own_students(two_schools):
    assert [x["student_id"] for x in _client("principal_a", "principal").get("/api/v1/students").json()] == ["A-1"]
    assert [x["student_id"] for x in _client("principal_b", "principal").get("/api/v1/students").json()] == ["B-1", "B-2"]


def test_ministry_can_read_students_and_bracelets_across_schools(two_schools):
    client = _client("ministry_x", "ministry")
    assert [x["student_id"] for x in client.get("/api/v1/students").json()] == ["A-1", "B-1", "B-2"]
    assert [x["bracelet_id"] for x in client.get("/api/v1/bracelets").json()] == ["BR-A1", "BR-B1"]
    assert client.get("/api/v1/students/B-1/profile").status_code == 200


def test_teacher_cannot_read_another_school_student(two_schools):
    client = _client("teacher_a", "teacher")
    assert client.get("/api/v1/students/B-1/profile").status_code == 404
    assert client.get("/api/v1/students/B-1/behavioral-history").status_code == 404


def test_risk_and_agent_student_reads_obey_school_scope(two_schools):
    teacher = _client("teacher_a", "teacher")
    ministry = _client("ministry_x", "ministry")

    school_risk = teacher.get("/api/v1/risk/attendance")
    assert school_risk.status_code == 200
    assert {row["student_id"] for row in school_risk.json()["students"]} == {"A-1"}
    assert teacher.get("/api/v1/risk/attendance/B-1").status_code == 404
    assert teacher.get("/api/v1/agent/recommendations/B-1").status_code == 404

    ministry_risk = ministry.get("/api/v1/risk/attendance")
    assert ministry_risk.status_code == 200
    assert {row["student_id"] for row in ministry_risk.json()["students"]} == {"A-1", "B-1", "B-2"}
    assert ministry.get("/api/v1/agent/recommendations/B-1").status_code == 200


def test_principal_cannot_read_or_mutate_another_school_student(two_schools, db_session_factory):
    client = _client("principal_a", "principal")
    assert client.patch("/api/v1/students/B-1", json={"name": "hijack"}).status_code == 404
    assert client.delete("/api/v1/students/B-1").status_code == 404
    assert client.patch("/api/v1/bracelets/BR-B1", json={"notes": "x"}).status_code == 404
    assert client.delete("/api/v1/bracelets/BR-B1").status_code == 404
    with db_session_factory() as db:
        assert db.get(orm.Student, "B-1").name == "B-1"


def test_principal_created_student_is_assigned_to_authenticated_school(two_schools, db_session_factory):
    payload = {"student_id": "A-2", "name": "New", "grade": "5", "class_section": "1", "parent_id": "P-A2"}
    response = _client("principal_a", "principal").post("/api/v1/students", json=payload)
    assert response.status_code == 201
    with db_session_factory() as db:
        assert db.get(orm.Student, "A-2").school_id == SCHOOL_A


def test_cannot_assign_bracelet_to_student_in_another_school(two_schools):
    payload = {"bracelet_id": "BR-X", "student_id": "B-2", "mac_address": "AA:BB:CC:DD:EE:99"}
    assert _client("principal_a", "principal").post("/api/v1/bracelets", json=payload).status_code == 400


@pytest.mark.parametrize("method,path,payload", [
    ("post", "/api/v1/students", {"student_id": "M-1", "name": "No", "grade": "5", "class_section": "1", "parent_id": "P-M"}),
    ("patch", "/api/v1/students/A-1", {"name": "No"}),
    ("delete", "/api/v1/students/A-1", None),
    ("post", "/api/v1/bracelets", {"bracelet_id": "BR-M", "student_id": "A-1", "mac_address": "AA:BB:CC:DD:EE:88"}),
    ("patch", "/api/v1/bracelets/BR-A1", {"notes": "No"}),
    ("delete", "/api/v1/bracelets/BR-A1", None),
    ("post", "/api/v1/bracelets/BR-A1/ping", {"zone_id": "zone-a"}),
])
def test_ministry_is_read_only_for_student_and_bracelet_records(two_schools, method, path, payload):
    client = _client("ministry_x", "ministry")
    response = getattr(client, method)(path, json=payload) if payload is not None else getattr(client, method)(path)
    assert response.status_code == 403
