"""DB-backed persistence for Unit 15 teacher feedback."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models as orm
from app.models import AgentFeedback, EngagementState
from app.services import seed_data
from app.services.pedagogical_agent import PedagogicalAgentService


def load_feedback(db: Session) -> list[AgentFeedback]:
    rows = db.scalars(select(orm.AgentFeedbackRecord).order_by(orm.AgentFeedbackRecord.recorded_at))
    return [
        AgentFeedback(
            feedback_id=r.feedback_id,
            session_id=r.session_id,
            student_id=r.student_id,
            predicted_state=EngagementState(r.predicted_state),
            confirmed_state=EngagementState(r.confirmed_state),
            teacher_notes=r.teacher_notes,
            recorded_at=r.recorded_at,
        )
        for r in rows
    ]


def build_agent(db: Session, *, include_feedback: bool = True) -> PedagogicalAgentService:
    """Build a service, optionally loading persisted teacher feedback."""
    return PedagogicalAgentService(
        snapshots=seed_data.engagement_snapshots,
        feedback_log=load_feedback(db) if include_feedback else [],
        video_log_dir=settings.video_log_dir,
    )


def save_feedback(db: Session, entry: AgentFeedback) -> None:
    db.add(
        orm.AgentFeedbackRecord(
            feedback_id=entry.feedback_id,
            session_id=entry.session_id,
            student_id=entry.student_id,
            predicted_state=entry.predicted_state.value,
            confirmed_state=entry.confirmed_state.value,
            teacher_notes=entry.teacher_notes,
            recorded_at=entry.recorded_at,
        )
    )
    db.commit()
