"""School-scoped API for proposing, approving and completing agent review tasks."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.deps import get_current_school_id, require_principal
from app.db.models import User
from app.db.session import get_db
from app.services.agent_action_workflow import (
    approve_review_task, complete_review_task, list_review_tasks,
    propose_review_task, reject_review_task,
)

router = APIRouter(prefix="/agent/actions", tags=["agent-action-approval"])


class ProposeReviewTask(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_request_id: UUID
    action_kind: Literal[
        "review_attendance_trend",
        "review_safety_signals",
        "review_operational_readiness",
        "verify_evidence_quality",
    ]


class ReviewTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    action_id: str
    school_id: str
    source_request_id: str
    action_kind: str
    title: str
    description: str
    assigned_role: str
    status: str
    proposed_by_user_id: int
    approved_by_user_id: int | None
    completed_by_user_id: int | None
    created_at: datetime
    approved_at: datetime | None
    completed_at: datetime | None


@router.post("", response_model=ReviewTaskResponse, status_code=201)
def propose_task(
    payload: ProposeReviewTask,
    user: User = Depends(require_principal),
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> ReviewTaskResponse:
    task = propose_review_task(
        db, school_id=school_id, user_id=user.id,
        source_request_id=str(payload.source_request_id), action_kind=payload.action_kind,
    )
    return ReviewTaskResponse.model_validate(task)


@router.get("", response_model=list[ReviewTaskResponse])
def get_tasks(
    _user: User = Depends(require_principal),
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> list[ReviewTaskResponse]:
    return [ReviewTaskResponse.model_validate(item) for item in list_review_tasks(db, school_id=school_id)]


@router.post("/{action_id}/approve", response_model=ReviewTaskResponse)
def approve_task(
    action_id: str,
    user: User = Depends(require_principal),
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> ReviewTaskResponse:
    return ReviewTaskResponse.model_validate(
        approve_review_task(db, action_id=action_id, school_id=school_id, approver_user_id=user.id)
    )


@router.post("/{action_id}/reject", response_model=ReviewTaskResponse)
def reject_task(
    action_id: str,
    user: User = Depends(require_principal),
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> ReviewTaskResponse:
    return ReviewTaskResponse.model_validate(
        reject_review_task(db, action_id=action_id, school_id=school_id, reviewer_user_id=user.id)
    )


@router.post("/{action_id}/complete", response_model=ReviewTaskResponse)
def complete_task(
    action_id: str,
    user: User = Depends(require_principal),
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> ReviewTaskResponse:
    return ReviewTaskResponse.model_validate(
        complete_review_task(db, action_id=action_id, school_id=school_id, user_id=user.id)
    )
