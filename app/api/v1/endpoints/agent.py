"""Unit 15: Pedagogical Behavioral Intelligence Agent — API endpoints.

Exposes:
  GET  /agent/insights          — session summary (engagement, flags, mismatches)
  POST /agent/feedback          — teacher performance annotation
  GET  /agent/feedback/metrics  — self-evaluation metrics
  GET  /agent/baselines         — daily per-student engagement baselines
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.models import EngagementState
from app.services import seed_data
from app.services.pedagogical_agent import PedagogicalAgentService
from app.core.config import settings

router = APIRouter(prefix="/agent", tags=["agent"])

# Module-level service instance backed by seed_data stores.
# Initialised lazily on first request so seed_data.populate() has already run.
_agent: Optional[PedagogicalAgentService] = None


def _get_agent() -> PedagogicalAgentService:
    global _agent  # noqa: PLW0603
    if _agent is None:
        _agent = PedagogicalAgentService(
            snapshots=seed_data.engagement_snapshots,
            feedback_log=seed_data.agent_feedback_log,
            video_log_dir=settings.video_log_dir,
        )
    return _agent


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
def get_session_insights(session_id: Optional[str] = None) -> dict[str, object]:
    """Return AI session summary: top engaged students, disengagement flags, and
    audio-visual mismatches.  Optionally filter to a specific session_id."""
    return _get_agent().get_session_insights(session_id=session_id)


@router.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_feedback(payload: FeedbackPayload) -> FeedbackResponse:
    """Accept a teacher annotation confirming or correcting a Unit 15 prediction.

    Each submission is logged in memory and appended to
    `<video_log_dir>/agent_performance.jsonl` for audit and offline analysis.
    """
    agent = _get_agent()
    # Verify student exists
    student = next((s for s in seed_data.students if s.student_id == payload.student_id), None)
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
def get_feedback_metrics() -> dict[str, object]:
    """Return precision/recall-style accuracy metrics derived from teacher feedback."""
    return _get_agent().compute_feedback_metrics()


@router.get("/baselines")
def get_baselines() -> dict[str, object]:
    """Return the most recent nightly-computed per-student daily engagement baselines."""
    agent = _get_agent()
    baselines = agent.get_baselines()
    # If baselines have not been computed yet (first run), compute them now.
    if not baselines:
        baselines = agent.compute_daily_baselines()
    return {"baselines": baselines, "total_students": len(baselines)}
