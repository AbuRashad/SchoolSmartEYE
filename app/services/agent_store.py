"""DB-backed persistence for Unit 15 teacher feedback with tenant filtering."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models as orm
from app.models import AgentFeedback, EngagementState
from app.services import seed_data
from app.services.pedagogical_agent import PedagogicalAgentService


def load_feedback(
    db: Session, *, student_ids: set[str] | None = None
) -> list[AgentFeedback]:
    stmt = select(orm.AgentFeedbackRecord).order_by(orm.AgentFeedbackRecord.recorded_at)
    if student_ids is not None:
        if not student_ids:
            return []
        stmt = stmt.where(orm.AgentFeedbackRecord.student_id.in_(student_ids))
    rows = db.scalars(stmt)
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


def build_agent(
    db: Session, *, include_feedback: bool = True, school_id: str | None = None
) -> PedagogicalAgentService:
    """Build an agent whose snapshots and feedback are restricted to one school.

    A missing school_id is reserved for the explicitly cross-school Ministry read
    surface. School callers must pass their authenticated school ID.
    """
    student_ids = None
    snapshots = seed_data.engagement_snapshots
    if school_id is not None:
        student_ids = set(
            db.scalars(
                select(orm.Student.student_id).where(orm.Student.school_id == school_id)
            ).all()
        )
        snapshots = [s for s in snapshots if s.student_id in student_ids]

    return PedagogicalAgentService(
        snapshots=snapshots,
        feedback_log=load_feedback(db, student_ids=student_ids) if include_feedback else [],
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
