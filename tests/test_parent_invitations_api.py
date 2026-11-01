from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import verify_password
from app.db import models as orm
from app.services import seed_data

API = "/api/v1"


def _invite(client, student_id="STU-2024-0847", username="parent.new"):
    return client.post(f"{API}/parent/invitations", json={
        "student_id": student_id,
        "parent_username": username,
        "parent_full_name": "New Parent",
        "verification_method": "school_records",
    })


def test_invitation_acceptance_creates_parent_and_verified_link(client, db_session_factory):
    seed_data.populate()
    issued = _invite(client)
    assert issued.status_code == 201
    data = issued.json()
    token = data["invitation_token"]
    with db_session_factory() as db:
        invitation = db.get(orm.ParentInvitation, data["invitation_id"])
        assert invitation.token_hash != token
        assert len(invitation.token_hash) == 64
    accepted = client.post(f"{API}/parent/invitations/accept", json={
        "invitation_token": token, "password": "Strong-Parent-Password-2026!"
    })
    assert accepted.status_code == 200
    assert accepted.json()["username"] == "parent.new"
    assert accepted.json()["role"] == "parent"
    with db_session_factory() as db:
        parent = db.scalar(select(orm.User).where(orm.User.username == "parent.new"))
        link = db.scalar(select(orm.ParentStudentLink).where(orm.ParentStudentLink.user_id == parent.id))
        invitation = db.scalar(select(orm.ParentInvitation).where(orm.ParentInvitation.id == data["invitation_id"]))
        assert parent.role == "parent"
        assert verify_password("Strong-Parent-Password-2026!", parent.hashed_password)
        assert link.student_id == "STU-2024-0847"
        assert link.school_id == "DEMO-SCHOOL-001"
        assert link.verified_by_user_id == invitation.invited_by_user_id
        assert invitation.accepted_at is not None
    replay = client.post(f"{API}/parent/invitations/accept", json={
        "invitation_token": token, "password": "Another-Strong-Password-2026!"
    })
    assert replay.status_code == 400


def test_invitation_is_school_scoped_and_parent_cannot_issue(client, db_session_factory):
    seed_data.populate()
    foreign = client.post(f"{API}/parent/invitations", json={
        "student_id": "NOT-IN-DEMO-SCHOOL", "parent_username": "foreign.parent",
        "parent_full_name": "Foreign Parent", "verification_method": "in_person",
    })
    assert foreign.status_code == 404
    issued = _invite(client)
    assert issued.status_code == 201
    token = issued.json()["invitation_token"]
    parent_token = __import__("app.core.security", fromlist=["create_access_token"]).create_access_token(
        "new.parent", "parent"
    )
    denied = client.post(f"{API}/parent/invitations", json={
        "student_id": "STU-2024-0847", "parent_username": "another.parent",
        "parent_full_name": "Another Parent", "verification_method": "in_person",
    }, headers={"Authorization": f"Bearer {parent_token}"})
    assert denied.status_code == 403
    assert token


def test_invitation_expiry_revocation_and_unknown_token(client, db_session_factory):
    seed_data.populate()
    issued = _invite(client)
    token = issued.json()["invitation_token"]
    invitation_id = issued.json()["invitation_id"]
    unknown = client.post(f"{API}/parent/invitations/accept", json={
        "invitation_token": "x" * 43, "password": "Strong-Parent-Password-2026!"
    })
    assert unknown.status_code == 400
    revoked = client.delete(f"{API}/parent/invitations/{invitation_id}")
    assert revoked.status_code == 204
    assert client.post(f"{API}/parent/invitations/accept", json={
        "invitation_token": token, "password": "Strong-Parent-Password-2026!"
    }).status_code == 400

    issued2 = _invite(client, username="parent.expired")
    with db_session_factory() as db:
        item = db.get(orm.ParentInvitation, issued2.json()["invitation_id"])
        item.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    assert client.post(f"{API}/parent/invitations/accept", json={
        "invitation_token": issued2.json()["invitation_token"],
        "password": "Strong-Parent-Password-2026!"
    }).status_code == 400


def test_invitation_name_collision_does_not_create_or_escalate_user(client, db_session_factory):
    seed_data.populate()
    issued = _invite(client, username="principal")
    assert issued.status_code == 409
    issued = _invite(client)
    token = issued.json()["invitation_token"]
    # Claiming the reserved username before acceptance invalidates the invitation.
    with db_session_factory() as db:
        db.add(orm.User(username="parent.new", full_name="Existing Teacher",
                        hashed_password="not-a-real-hash", role="teacher", is_active=True))
        db.commit()
    response = client.post(f"{API}/parent/invitations/accept", json={
        "invitation_token": token, "password": "Strong-Parent-Password-2026!"
    })
    assert response.status_code == 409
    with db_session_factory() as db:
        assert db.scalar(select(orm.User).where(orm.User.username == "parent.new")).role == "teacher"
