"""Human-approved, idempotent and school-scoped agent action workflow."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import AgentActionAuditEvent, AgentActionTask, AgentRunRecord

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

_RULE_VERSION = "1.0"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _record_event(
    db: Session,
    *,
    task: AgentActionTask,
    event_type: str,
    actor_type: str,
    actor_user_id: int | None,
    from_status: str | None,
    to_status: str | None,
    details: dict[str, Any] | None = None,
) -> AgentActionAuditEvent:
    """Append a lifecycle event. No update/delete operation is exposed for events."""
    event = AgentActionAuditEvent(
        event_id=str(uuid.uuid4()),
        school_id=task.school_id,
        action_id=task.action_id,
        source_request_id=task.source_request_id,
        event_type=event_type,
        actor_type=actor_type,
        actor_user_id=actor_user_id,
        from_status=from_status,
        to_status=to_status,
        event_metadata=details or {},
        created_at=_utcnow(),
    )
    db.add(event)
    return event


def propose_review_task(
    db: Session, *, school_id: str, user_id: int, source_request_id: str,
    action_kind: str, actor_type: str = "user",
    signal_codes: list[str] | None = None,
) -> AgentActionTask:
    """Persist one predefined proposal; the school/run/action key is idempotent."""
    run = db.scalar(select(AgentRunRecord).where(
        AgentRunRecord.request_id == source_request_id,
        AgentRunRecord.school_id == school_id,
    ))
    if run is None:
        raise HTTPException(status_code=404, detail="Source agent run not found in this school")
    template = _ACTION_TEMPLATES.get(action_kind)
    if template is None:
        raise HTTPException(status_code=422, detail="Unsupported agent action")

    existing = db.scalar(select(AgentActionTask).where(
        AgentActionTask.school_id == school_id,
        AgentActionTask.source_request_id == source_request_id,
        AgentActionTask.action_kind == action_kind,
    ))
    if existing is not None:
        return existing

    title, description, assigned_role = template
    task = AgentActionTask(
        action_id=str(uuid.uuid4()), school_id=school_id,
        source_request_id=source_request_id, action_kind=action_kind,
        title=title, description=description, assigned_role=assigned_role,
        status="pending_approval", proposed_by_user_id=user_id, created_at=_utcnow(),
    )
    details = {
        "trigger": "orchestrator_result" if actor_type == "agent" else "manual_proposal",
        "rule_version": _RULE_VERSION,
        "signal_codes": signal_codes or [],
    }
    try:
        # Savepoint lets a concurrent duplicate lose the unique-key race without
        # rolling back the already-persisted orchestration run.
        with db.begin_nested():
            db.add(task)
            db.flush()
            _record_event(
                db, task=task, event_type="proposed", actor_type=actor_type,
                actor_user_id=None if actor_type == "agent" else user_id,
                from_status=None, to_status="pending_approval", details=details,
            )
            db.flush()
    except IntegrityError:
        existing = db.scalar(select(AgentActionTask).where(
            AgentActionTask.school_id == school_id,
            AgentActionTask.source_request_id == source_request_id,
            AgentActionTask.action_kind == action_kind,
        ))
        if existing is not None:
            return existing
        raise
    db.commit()
    db.refresh(task)
    return task


def derive_action_proposals(result: dict[str, Any]) -> dict[str, list[str]]:
    """Map validated deterministic evidence to a bounded set of predefined actions.

    AI-generated prose is deliberately ignored. Only typed aggregate evidence and
    provenance fields in the persisted orchestrator result drive these rules.
    """
    metrics: dict[str, int | float] = {}
    for item in result.get("evidence", []):
        if not isinstance(item, dict):
            continue
        key = item.get("description", "")
        prefix = "Aggregate metric: "
        value = item.get("value")
        if isinstance(key, str) and key.startswith(prefix):
            name = key[len(prefix):]
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                metrics[name] = value

    proposals: dict[str, list[str]] = {}
    attendance = metrics.get("attendance_rate")
    if attendance is not None and attendance < 90:
        proposals["review_attendance_trend"] = ["attendance_below_review_threshold"]

    safety_signals: list[str] = []
    incidents = metrics.get("incidents_today")
    crowd = metrics.get("avg_crowd_density")
    if incidents is not None and incidents > 0:
        safety_signals.append("nonzero_incident_count")
    if crowd is not None and crowd >= 0.75:
        safety_signals.append("elevated_aggregate_crowd_indicator")
    if safety_signals:
        proposals["review_safety_signals"] = safety_signals

    operational_signals: list[str] = []
    uptime = metrics.get("uptime_percent")
    cameras = metrics.get("active_cameras")
    if uptime is not None and uptime < 99:
        operational_signals.append("uptime_below_review_threshold")
    if cameras == 0:
        operational_signals.append("no_active_cameras_reported")
    if operational_signals:
        proposals["review_operational_readiness"] = operational_signals

    report = result.get("report") if isinstance(result.get("report"), dict) else {}
    evidence_count = report.get("evidence_count", len(result.get("evidence", [])))
    data_status = report.get("data_status", "unknown")
    if data_status != "live" or not isinstance(evidence_count, int) or evidence_count <= 0:
        reasons = []
        if data_status != "live":
            reasons.append("source_provenance_requires_verification")
        if not isinstance(evidence_count, int) or evidence_count <= 0:
            reasons.append("no_validated_evidence")
        proposals["verify_evidence_quality"] = reasons

    return proposals


def propose_actions_for_run(
    db: Session, *, school_id: str, source_request_id: str,
) -> list[AgentActionTask]:
    """Create deduplicated review proposals from a persisted run's deterministic evidence."""
    run = db.scalar(select(AgentRunRecord).where(
        AgentRunRecord.request_id == source_request_id,
        AgentRunRecord.school_id == school_id,
    ))
    if run is None:
        raise HTTPException(status_code=404, detail="Source agent run not found in this school")
    proposals = derive_action_proposals(run.result or {})
    tasks: list[AgentActionTask] = []
    for action_kind, signal_codes in proposals.items():
        task = propose_review_task(
            db, school_id=school_id, user_id=run.requested_by_user_id,
            source_request_id=source_request_id, action_kind=action_kind,
            actor_type="agent", signal_codes=signal_codes,
        )
        tasks.append(task)
    return tasks


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
    previous = task.status
    task.status = "open"
    task.approved_by_user_id = approver_user_id
    task.approved_at = _utcnow()
    _record_event(
        db, task=task, event_type="approved", actor_type="user",
        actor_user_id=approver_user_id, from_status=previous, to_status="open",
    )
    db.commit()
    db.refresh(task)
    return task


def reject_review_task(
    db: Session, *, action_id: str, school_id: str, reviewer_user_id: int,
) -> AgentActionTask:
    task = _get_pending(db, action_id, school_id)
    if task.proposed_by_user_id == reviewer_user_id:
        raise HTTPException(status_code=403, detail="A different authorised user must review this request")
    previous = task.status
    task.status = "rejected"
    _record_event(
        db, task=task, event_type="rejected", actor_type="user",
        actor_user_id=reviewer_user_id, from_status=previous, to_status="rejected",
    )
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
    previous = task.status
    task.status = "completed"
    task.completed_by_user_id = user_id
    task.completed_at = _utcnow()
    _record_event(
        db, task=task, event_type="completed", actor_type="user",
        actor_user_id=user_id, from_status=previous, to_status="completed",
    )
    db.commit()
    db.refresh(task)
    return task


def list_review_tasks(db: Session, *, school_id: str) -> list[AgentActionTask]:
    return list(db.scalars(
        select(AgentActionTask).where(AgentActionTask.school_id == school_id)
        .order_by(AgentActionTask.created_at.desc()).limit(100)
    ))


def list_action_audit_events(
    db: Session, *, action_id: str, school_id: str,
) -> list[AgentActionAuditEvent]:
    task = db.scalar(select(AgentActionTask).where(
        AgentActionTask.action_id == action_id,
        AgentActionTask.school_id == school_id,
    ))
    if task is None:
        raise HTTPException(status_code=404, detail="Action request not found")
    return list(db.scalars(
        select(AgentActionAuditEvent)
        .where(
            AgentActionAuditEvent.action_id == action_id,
            AgentActionAuditEvent.school_id == school_id,
        )
        .order_by(AgentActionAuditEvent.created_at.asc(), AgentActionAuditEvent.id.asc())
    ))
