"""DB-backed persistence for Unit 15 teacher feedback."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models as orm
from app.models import AgentFeedback, EngagementState
from app.services import seed_data
from app.services.pedagogical_agent import PedagogicalAgentService


def load_feedback(db: Session, school_id: str) -> list[AgentFeedback]:
    rows = db.scalars(
        select(orm.AgentFeedbackRecord)
        .join(orm.Student, orm.Student.student_id == orm.AgentFeedbackRecord.student_id)
        .where(orm.Student.school_id == school_id)
        .order_by(orm.AgentFeedbackRecord.recorded_at)
    )
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
    db: Session,
    school_id: str,
    *,
    include_feedback: bool = True,
) -> PedagogicalAgentService:
    """Build a strictly school-scoped service; unknown/unassigned students are excluded."""
    student_ids = set(db.scalars(
        select(orm.Student.student_id).where(orm.Student.school_id == school_id)
    ))
    snapshots = [item for item in seed_data.engagement_snapshots if item.student_id in student_ids]
    return PedagogicalAgentService(
        snapshots=snapshots,
        feedback_log=load_feedback(db, school_id) if include_feedback else [],
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
