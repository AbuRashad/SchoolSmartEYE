"""Unit 15: Pedagogical Behavioral Intelligence Agent — API endpoints.

Exposes:
  GET  /agent/insights          — session summary (engagement, flags, mismatches)
  POST /agent/feedback          — teacher performance annotation
  GET  /agent/feedback/metrics  — self-evaluation metrics
  GET  /agent/baselines         — daily per-student engagement baselines
  GET  /agent/recommendations/{student_id} — history/feedback-aware recommendations

Feedback is persisted in the database. Writing feedback requires teacher+ access;
read endpoints stay public for frontend compatibility.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models as orm
from app.db.session import get_db
from app.models import EngagementState
from app.api.deps import require_school_staff, require_teacher, school_scope
from app.services import agent_store

router = APIRouter(prefix="/agent", tags=["agent"], dependencies=[Depends(require_teacher)])

# ── Request / response schemas ────────────────────────────────────────────────


class FeedbackPayload(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    student_id: str = Field(..., min_length=1, max_length=64)
    predicted_state: EngagementState
    confirmed_state: EngagementState
    teacher_notes: str = Field(default="", max_length=1024)


class FeedbackResponse(BaseModel):
    feedback_id: str
    session_id: str
    student_id: str
    predicted_state: str
    confirmed_state: str
    teacher_notes: str
    recorded_at: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/insights")
def get_session_insights(
    session_id: Optional[str] = None, db: Session = Depends(get_db),
    user: orm.User = Depends(require_teacher),
) -> dict[str, object]:
    """Return AI session summary: top engaged students, disengagement flags, and
    audio-visual mismatches.  Optionally filter to a specific session_id."""
    return agent_store.build_agent(db, school_id=school_scope(user)).get_session_insights(session_id=session_id)


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_school_staff)],
)
def submit_feedback(payload: FeedbackPayload, db: Session = Depends(get_db), user: orm.User = Depends(require_school_staff)) -> FeedbackResponse:
    """Accept a teacher annotation confirming or correcting a Unit 15 prediction.

    Each submission is stored in the database and appended to
    `<video_log_dir>/agent_performance.jsonl` for audit and offline analysis.
    """
    agent = agent_store.build_agent(db, include_feedback=False, school_id=school_scope(user))
    # Verify student exists
    student = db.scalar(select(orm.Student).where(orm.Student.student_id == payload.student_id, orm.Student.school_id == school_scope(user)))
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student {payload.student_id!r} not found",
        )
    feedback_id = f"FB-{uuid.uuid4().hex[:8].upper()}"
    entry = agent.record_feedback(
        feedback_id=feedback_id,
        session_id=payload.session_id,
        student_id=payload.student_id,
        predicted_state=payload.predicted_state,
        confirmed_state=payload.confirmed_state,
        teacher_notes=payload.teacher_notes,
    )
    agent_store.save_feedback(db, entry)
    return FeedbackResponse(
        feedback_id=entry.feedback_id,
        session_id=entry.session_id,
        student_id=entry.student_id,
        predicted_state=entry.predicted_state.value,
        confirmed_state=entry.confirmed_state.value,
        teacher_notes=entry.teacher_notes,
        recorded_at=entry.recorded_at.isoformat(),
    )


@router.get("/feedback/metrics")
def get_feedback_metrics(
    db: Session = Depends(get_db), user: orm.User = Depends(require_teacher)
) -> dict[str, object]:
    """Return precision/recall-style accuracy metrics derived from teacher feedback."""
    agent = agent_store.build_agent(db, school_id=school_scope(user))
    return {**agent.compute_feedback_metrics(), "calibration": agent.get_feedback_calibration()}


@router.get("/baselines")
def get_baselines(
    db: Session = Depends(get_db), user: orm.User = Depends(require_teacher)
) -> dict[str, object]:
    """Return the most recent nightly-computed per-student daily engagement baselines."""
    baselines = agent_store.build_agent(db, include_feedback=False, school_id=school_scope(user)).compute_daily_baselines()
    return {"baselines": baselines, "total_students": len(baselines)}


@router.get("/recommendations/{student_id}")
def get_recommendations(
    student_id: str,
    db: Session = Depends(get_db),
    user: orm.User = Depends(require_teacher),
) -> dict[str, object]:
    """Recommended actions for a student within the caller's authorised school scope."""
    student_stmt = select(orm.Student).where(orm.Student.student_id == student_id)
    scope = school_scope(user)
    if scope is not None:
        student_stmt = student_stmt.where(orm.Student.school_id == scope)
    if db.scalar(student_stmt) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student {student_id!r} not found",
        )
    return agent_store.build_agent(db, school_id=scope).get_recommendations(student_id)
