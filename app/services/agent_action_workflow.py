"""Human approval workflow for a tightly allowlisted SchoolSmartEYE agent action surface."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AgentActionTask, AgentRunRecord

# Fixed server-owned templates prevent an agent or caller from injecting arbitrary
# messages, student identifiers, or external commands into the action queue.
_ACTION_TEMPLATES = {
    "review_attendance_trend": (
        "Review school-wide attendance trend",
        "Review the aggregate attendance trend, verify source completeness, and record an appropriate school-level response.",
        "principal",
    ),
    "review_safety_signals": (
        "Review school-wide safety signals",
        "Verify the reported aggregate safety signals with authorised staff and document the outcome.",
        "principal",
    ),
    "review_operational_readiness": (
        "Review operational readiness",
        "Check reported service and operational indicators, confirm source freshness, and record any required follow-up.",
        "principal",
    ),
    "verify_evidence_quality": (
        "Verify evidence quality and provenance",
        "Check the provenance, completeness, and freshness of the evidence used in the school-wide agent review.",
        "teacher",
    ),
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def propose_review_task(
    db: Session, *, school_id: str, user_id: int, source_request_id: str,
    action_kind: str,
) -> AgentActionTask:
    """Persist a pending, predefined internal review task; perform no side effect."""
    run = db.scalar(select(AgentRunRecord).where(
        AgentRunRecord.request_id == source_request_id,
        AgentRunRecord.school_id == school_id,
    ))
    if run is None:
        raise HTTPException(status_code=404, detail="Source agent run not found in this school")
    template = _ACTION_TEMPLATES.get(action_kind)
    if template is None:
        raise HTTPException(status_code=422, detail="Unsupported agent action")
    title, description, assigned_role = template
    task = AgentActionTask(
        action_id=str(uuid.uuid4()), school_id=school_id,
        source_request_id=source_request_id, action_kind=action_kind,
        title=title, description=description, assigned_role=assigned_role,
        status="pending_approval", proposed_by_user_id=user_id, created_at=_utcnow(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _get_pending(db: Session, action_id: str, school_id: str) -> AgentActionTask:
    task = db.scalar(
        select(AgentActionTask)
        .where(AgentActionTask.action_id == action_id, AgentActionTask.school_id == school_id)
        .with_for_update()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Action request not found")
    if task.status != "pending_approval":
        raise HTTPException(status_code=409, detail="Only pending requests can be reviewed")
    return task


def approve_review_task(
    db: Session, *, action_id: str, school_id: str, approver_user_id: int,
) -> AgentActionTask:
    """Independent approval transitions the proposal into an actionable internal task."""
    task = _get_pending(db, action_id, school_id)
    if task.proposed_by_user_id == approver_user_id:
        raise HTTPException(status_code=403, detail="A different authorised user must approve this request")
    task.status = "open"
    task.approved_by_user_id = approver_user_id
    task.approved_at = _utcnow()
    db.commit()
    db.refresh(task)
    return task


def reject_review_task(
    db: Session, *, action_id: str, school_id: str, reviewer_user_id: int,
) -> AgentActionTask:
    task = _get_pending(db, action_id, school_id)
    if task.proposed_by_user_id == reviewer_user_id:
        raise HTTPException(status_code=403, detail="A different authorised user must review this request")
    task.status = "rejected"
    db.commit()
    db.refresh(task)
    return task


def complete_review_task(
    db: Session, *, action_id: str, school_id: str, user_id: int,
) -> AgentActionTask:
    task = db.scalar(
        select(AgentActionTask)
        .where(AgentActionTask.action_id == action_id, AgentActionTask.school_id == school_id)
        .with_for_update()
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Action request not found")
    if task.status != "open":
        raise HTTPException(status_code=409, detail="Only open tasks can be completed")
    task.status = "completed"
    task.completed_by_user_id = user_id
    task.completed_at = _utcnow()
    db.commit()
    db.refresh(task)
    return task


def list_review_tasks(db: Session, *, school_id: str) -> list[AgentActionTask]:
    return list(db.scalars(
        select(AgentActionTask).where(AgentActionTask.school_id == school_id)
        .order_by(AgentActionTask.created_at.desc()).limit(100)
    ))
