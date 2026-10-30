"""Persistent, school-scoped human review queue for camera-derived events.

Only event metadata and an opaque evidence reference are stored here. This
endpoint does not ingest video, identify people, or make an automated safety
decision. A designated school principal owns every final review decision.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_principal
from app.db.models import CameraReviewEvent, GovernanceAuditEvent, User
from app.db.session import get_db

router = APIRouter(prefix="/camera-reviews", tags=["camera-reviews"])

ReviewStatus = Literal["pending", "confirmed", "dismissed", "needs_follow_up"]
Severity = Literal["low", "medium", "high", "critical"]


class CameraEventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: str = Field(min_length=8, max_length=128)
    camera_id: str | None = Field(default=None, min_length=1, max_length=64)
    zone_id: str | None = Field(default=None, min_length=1, max_length=64)
    event_type: str = Field(min_length=1, max_length=64)
    severity: Severity = "low"
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(min_length=1, max_length=512)
    detected_at: datetime
    evidence_ref: str | None = Field(default=None, max_length=256)

    @field_validator("detected_at")
    @classmethod
    def normalize_detected_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("detected_at must include a timezone")
        return value.astimezone(timezone.utc)


class ReviewDecisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["confirmed", "dismissed", "needs_follow_up"]
    note: str = Field(default="", max_length=1024)


def _school_principal(user: User) -> str:
    if user.role != "principal" or not user.school_id:
        raise HTTPException(status_code=403, detail="A principal assigned to a school is required")
    return user.school_id


def _serialize(event: CameraReviewEvent) -> dict[str, object]:
    return {
        "event_id": event.event_id,
        "camera_id": event.camera_id,
        "zone_id": event.zone_id,
        "event_type": event.event_type,
        "severity": event.severity,
        "confidence": event.confidence,
        "summary": event.summary,
        "detected_at": event.detected_at.isoformat(),
        "evidence_ref": event.evidence_ref,
        "status": event.status,
        "created_at": event.created_at.isoformat(),
        "reviewed_by_user_id": event.reviewed_by_user_id,
        "reviewed_at": event.reviewed_at.isoformat() if event.reviewed_at else None,
        "review_note": event.review_note,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def enqueue_camera_event(
    payload: CameraEventIn,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(require_principal),
) -> dict[str, object]:
    """Persist an unverified camera event; it remains pending human review."""
    school_id = _school_principal(user)
    event = CameraReviewEvent(
        event_id=str(uuid.uuid4()),
        school_id=school_id,
        camera_id=payload.camera_id,
        zone_id=payload.zone_id,
        event_type=payload.event_type,
        severity=payload.severity,
        confidence=payload.confidence,
        summary=payload.summary,
        detected_at=payload.detected_at,
        evidence_ref=payload.evidence_ref,
        idempotency_key=payload.idempotency_key,
        status="pending",
        created_by_user_id=user.id,
    )
    db.add(event)
    try:
        db.flush()
        db.add(GovernanceAuditEvent(
            school_id=school_id,
            actor_user_id=user.id,
            event_type="camera_review.event_created",
            target_type="camera_review_event",
            target_id=event.event_id,
            details={"status": "pending", "event_type": event.event_type,
                     "severity": event.severity, "camera_id": event.camera_id},
        ))
        db.commit()
        db.refresh(event)
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(CameraReviewEvent).where(
            CameraReviewEvent.school_id == school_id,
            CameraReviewEvent.idempotency_key == payload.idempotency_key,
        ))
        if existing is None:
            raise HTTPException(status_code=409, detail="Event could not be persisted") from None
        if response is not None:
            response.status_code = status.HTTP_200_OK
        return _serialize(existing)
    return _serialize(event)


@router.get("")
def list_camera_events(
    review_status: ReviewStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=100),
    before_event_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_principal),
) -> dict[str, object]:
    """List only the authenticated principal's school's review events."""
    school_id = _school_principal(user)
    statement = select(CameraReviewEvent).where(CameraReviewEvent.school_id == school_id)
    if review_status:
        statement = statement.where(CameraReviewEvent.status == review_status)
    if before_event_id:
        cursor = db.get(CameraReviewEvent, before_event_id)
        if cursor is None or cursor.school_id != school_id:
            raise HTTPException(status_code=404, detail="Cursor event not found")
        statement = statement.where(CameraReviewEvent.created_at < cursor.created_at)
    events = db.scalars(
        statement.order_by(CameraReviewEvent.created_at.desc(), CameraReviewEvent.event_id.desc()).limit(limit)
    ).all()
    return {"school_id": school_id, "items": [_serialize(event) for event in events],
            "count": len(events), "next_before_event_id": events[-1].event_id if len(events) == limit else None}


@router.post("/{event_id}/review")
def review_camera_event(
    event_id: str,
    payload: ReviewDecisionIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_principal),
) -> dict[str, object]:
    """Record a human decision once; AI confidence never substitutes for review."""
    school_id = _school_principal(user)
    event = db.scalar(select(CameraReviewEvent).where(
        CameraReviewEvent.event_id == event_id,
        CameraReviewEvent.school_id == school_id,
    ))
    if event is None:
        raise HTTPException(status_code=404, detail="Camera event not found")
    if event.status != "pending":
        raise HTTPException(status_code=409, detail="Only pending events can receive a review decision")
    now = datetime.now(timezone.utc)
    event.status = payload.decision
    event.reviewed_by_user_id = user.id
    event.reviewed_at = now
    event.review_note = payload.note
    db.add(GovernanceAuditEvent(
        school_id=school_id,
        actor_user_id=user.id,
        event_type="camera_review.decision_recorded",
        target_type="camera_review_event",
        target_id=event.event_id,
        details={"decision": payload.decision, "previous_status": "pending"},
    ))
    db.commit()
    db.refresh(event)
    return _serialize(event)
