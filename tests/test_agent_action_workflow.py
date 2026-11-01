from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models import School, User
from app.services.agent_action_workflow import (
    approve_review_task,
    complete_review_task,
    list_review_tasks,
    propose_review_task,
    reject_review_task,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([
            School(school_id="school-a", name="Synthetic School A"),
            School(school_id="school-b", name="Synthetic School B"),
            User(id=1, username="principal-a", full_name="Principal A", hashed_password="x", role="principal"),
            User(id=2, username="principal-b", full_name="Principal B", hashed_password="x", role="principal"),
            User(id=3, username="principal-c", full_name="Principal C", hashed_password="x", role="principal"),
        ])
        session.commit()
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_action_requires_independent_human_approval_and_completes(db):
    task = propose_review_task(
        db, school_id="school-a", user_id=1, source_request_id=str(uuid.uuid4()),
        action_kind="review_safety_signals",
    )
    assert task.status == "pending_approval"
    assert task.title == "Review school-wide safety signals"

    with pytest.raises(HTTPException) as own_approval:
        approve_review_task(db, action_id=task.action_id, school_id="school-a", approver_user_id=1)
    assert own_approval.value.status_code == 403

    approved = approve_review_task(
        db, action_id=task.action_id, school_id="school-a", approver_user_id=2
    )
    assert approved.status == "open"
    assert approved.approved_by_user_id == 2
    assert approved.approved_at is not None

    completed = complete_review_task(
        db, action_id=task.action_id, school_id="school-a", user_id=2
    )
    assert completed.status == "completed"
    assert completed.completed_by_user_id == 2
    assert completed.completed_at is not None

    with pytest.raises(HTTPException) as duplicate:
        complete_review_task(db, action_id=task.action_id, school_id="school-a", user_id=2)
    assert duplicate.value.status_code == 409


def test_action_is_tenant_scoped_and_unknown_action_is_rejected(db):
    task = propose_review_task(
        db, school_id="school-a", user_id=1, source_request_id=str(uuid.uuid4()),
        action_kind="review_attendance_trend",
    )
    assert [item.action_id for item in list_review_tasks(db, school_id="school-a")] == [task.action_id]
    assert list_review_tasks(db, school_id="school-b") == []

    with pytest.raises(HTTPException) as wrong_school:
        approve_review_task(db, action_id=task.action_id, school_id="school-b", approver_user_id=2)
    assert wrong_school.value.status_code == 404

    with pytest.raises(HTTPException) as invalid_action:
        propose_review_task(
            db, school_id="school-a", user_id=1, source_request_id=str(uuid.uuid4()),
            action_kind="send_parent_message",
        )
    assert invalid_action.value.status_code == 422


def test_rejected_action_cannot_be_approved(db):
    task = propose_review_task(
        db, school_id="school-a", user_id=1, source_request_id=str(uuid.uuid4()),
        action_kind="verify_evidence_quality",
    )
    rejected = reject_review_task(
        db, action_id=task.action_id, school_id="school-a", reviewer_user_id=3
    )
    assert rejected.status == "rejected"
    with pytest.raises(HTTPException) as cannot_approve:
        approve_review_task(db, action_id=task.action_id, school_id="school-a", approver_user_id=2)
    assert cannot_approve.value.status_code == 409
