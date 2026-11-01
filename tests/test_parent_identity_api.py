from datetime import datetime, timezone

from app.core import security
from app.db import models as orm
from app.services import seed_data

API = "/api/v1"


def _create_parent(db_session_factory, username="parent.one"):
    with db_session_factory() as db:
        user = orm.User(
            username=username,
            full_name="Verified Parent",
            hashed_password=security.hash_password("Parent-Test-Password-123!"),
            role="parent",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id


def _parent_headers(username="parent.one"):
    token = security.create_access_token(username, "parent")
    return {"Authorization": f"Bearer {token}"}


def _link(client, student_id="STU-2024-0847", username="parent.one"):
    return client.post(
        f"{API}/parent/links",
        json={
            "student_id": student_id,
            "parent_username": username,
            "verification_method": "school_records",
        },
    )


def test_principal_can_create_verified_link_and_parent_sees_only_linked_student(
    client, db_session_factory
):
    seed_data.populate()
    _create_parent(db_session_factory)

    created = _link(client)
    assert created.status_code == 201
    assert created.json()["student_id"] == "STU-2024-0847"
    assert created.json()["parent_username"] == "parent.one"
    assert created.json()["is_active"] is True
    assert created.json()["verification_method"] == "school_records"

    headers = _parent_headers()
    students = client.get(f"{API}/parent/students", headers=headers)
    assert students.status_code == 200
    assert [item["student_id"] for item in students.json()] == ["STU-2024-0847"]

    summary = client.get(
        f"{API}/parent/students/STU-2024-0847/summary",
        headers=headers,
    )
    assert summary.status_code == 200
    assert summary.json()["student"]["student_id"] == "STU-2024-0847"
    assert "live location" in summary.json()["data_notice"].lower()
    assert all("parent_id" not in item for item in summary.json()["notifications"])


def test_parent_cannot_self_create_link_or_access_unlinked_student(
    client, db_session_factory
):
    seed_data.populate()
    _create_parent(db_session_factory)

    headers = _parent_headers()
    denied_link = client.post(
        f"{API}/parent/links",
        json={
            "student_id": "STU-2024-0847",
            "parent_username": "parent.one",
            "verification_method": "school_records",
        },
        headers=headers,
    )
    assert denied_link.status_code == 403

    assert client.get(f"{API}/parent/students", headers=headers).json() == []
    denied_summary = client.get(
        f"{API}/parent/students/STU-2024-0847/summary",
        headers=headers,
    )
    assert denied_summary.status_code == 404


def test_principal_cannot_link_student_from_another_school(
    client, db_session_factory
):
    seed_data.populate()
    _create_parent(db_session_factory)

    with db_session_factory() as db:
        db.add(orm.School(
            school_id="PARENT-FOREIGN-SCHOOL",
            name="Foreign Parent School",
            is_active=True,
        ))
        db.flush()
        db.add(orm.Student(
            student_id="PARENT-FOREIGN-STUDENT",
            school_id="PARENT-FOREIGN-SCHOOL",
            name="Foreign Student",
            grade="G8",
            class_section="B",
            parent_id="FOREIGN-PARENT-REF",
        ))
        db.commit()

    response = _link(client, student_id="PARENT-FOREIGN-STUDENT")
    assert response.status_code == 404
    assert "PARENT-FOREIGN-SCHOOL" not in response.text
    assert "PARENT-FOREIGN-STUDENT" not in response.text


def test_link_requires_existing_active_parent_account_and_duplicate_is_neutral(
    client, db_session_factory
):
    seed_data.populate()
    _create_parent(db_session_factory)

    missing = client.post(
        f"{API}/parent/links",
        json={
            "student_id": "STU-2024-0847",
            "parent_username": "not-a-parent",
            "verification_method": "in_person",
        },
    )
    assert missing.status_code == 404
    assert "not-a-parent" not in missing.text

    assert _link(client).status_code == 201
    duplicate = _link(client)
    assert duplicate.status_code == 409
    assert "parent.one" not in duplicate.text


def test_parent_summary_excludes_notifications_for_stale_parent_reference(
    client, db_session_factory
):
    seed_data.populate()
    _create_parent(db_session_factory)
    assert _link(client).status_code == 201

    with db_session_factory() as db:
        db.add(orm.Notification(
            notification_id="PARENT-WRONG-RECIPIENT",
            parent_id="OLD-PARENT-REFERENCE",
            student_id="STU-2024-0847",
            message="Should never be shown to the linked parent",
            notification_type="safety",
            sent_at=datetime.now(timezone.utc),
            read=False,
        ))
        db.commit()

    summary = client.get(
        f"{API}/parent/students/STU-2024-0847/summary",
        headers=_parent_headers(),
    )
    assert summary.status_code == 200
    ids = [item["notification_id"] for item in summary.json()["notifications"]]
    assert "PARENT-WRONG-RECIPIENT" not in ids


def test_principal_can_revoke_parent_link_and_parent_loses_access(
    client, db_session_factory
):
    seed_data.populate()
    _create_parent(db_session_factory)
    assert _link(client).status_code == 201

    revoked = client.delete(
        f"{API}/parent/links/STU-2024-0847/parent.one"
    )
    assert revoked.status_code == 204

    with db_session_factory() as db:
        link = db.scalar(
            __import__("sqlalchemy").select(orm.ParentStudentLink).where(
                orm.ParentStudentLink.student_id == "STU-2024-0847"
            )
        )
        principal = db.scalar(
            __import__("sqlalchemy").select(orm.User).where(orm.User.username == "principal")
        )
        assert link.is_active is False
        assert link.revoked_at is not None
        assert link.revoked_by_user_id == principal.id

    summary = client.get(
        f"{API}/parent/students/STU-2024-0847/summary",
        headers=_parent_headers(),
    )
    assert summary.status_code == 404
