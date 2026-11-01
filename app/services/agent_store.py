"""DB-backed persistence for Unit 15 teacher feedback."""
from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models as orm
from app.models import AgentFeedback, EngagementState
from app.services import seed_data
from app.services.pedagogical_agent import FEEDBACK_LOG_LOCK, PedagogicalAgentService


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
    with seed_data.engagement_snapshots_lock:
        # Restore missing synthetic trajectories only for known demo students in
        # non-production environments. Deleted students are absent from the DB
        # scope and therefore can never be re-seeded by this fallback.
        if school_id == "DEMO-SCHOOL-001" and not settings.is_production:
            existing_ids = {item.student_id for item in seed_data.engagement_snapshots}
            demo_ids = student_ids.intersection(seed_data._STUDENT_SESSION_PROFILES)
            missing_demo_ids = demo_ids - existing_ids
            if missing_demo_ids:
                seed_data._seed_engagement_snapshots(missing_demo_ids)
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



def purge_student_artifacts(student_id: str, video_log_dir: str | None = None) -> dict[str, int]:
    """Purge in-memory engagement snapshots and student-linked feedback JSONL.

    The JSONL rewrite fails closed on malformed records so an operator is not
    told erasure succeeded when the file could not be safely inspected.
    """
    with seed_data.engagement_snapshots_lock:
        before = len(seed_data.engagement_snapshots)
        seed_data.engagement_snapshots[:] = [
            item for item in seed_data.engagement_snapshots if item.student_id != student_id
        ]
        removed_snapshots = before - len(seed_data.engagement_snapshots)

    removed_feedback_logs = 0
    if video_log_dir:
        log_path = Path(video_log_dir) / "agent_performance.jsonl"
        with FEEDBACK_LOG_LOCK:
            if log_path.exists():
                retained: list[str] = []
                with log_path.open("r", encoding="utf-8") as handle:
                    for line in handle:
                        if not line.strip():
                            continue
                        try:
                            record = json.loads(line)
                        except json.JSONDecodeError as exc:
                            raise RuntimeError("Feedback log contains an unreadable record; erasure halted.") from exc
                        if not isinstance(record, dict):
                            raise RuntimeError("Feedback log contains an invalid record; erasure halted.")
                        if record.get("student_id") == student_id:
                            removed_feedback_logs += 1
                        else:
                            retained.append(json.dumps(record, ensure_ascii=False) + "\n")
                temporary = log_path.with_name(log_path.name + ".erasure-tmp")
                try:
                    with temporary.open("w", encoding="utf-8") as handle:
                        handle.writelines(retained)
                        handle.flush()
                        os.fsync(handle.fileno())
                    os.replace(temporary, log_path)
                finally:
                    if temporary.exists():
                        temporary.unlink()

    return {
        "engagement_snapshots": removed_snapshots,
        "feedback_log_entries": removed_feedback_logs,
    }
