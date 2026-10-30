"""School-scoped persistence and history for camera operational telemetry.

Only principals can submit telemetry in this phase. An authenticated edge-agent
identity and device credential flow must be added before unattended device use.
No frames, images, audio, or person-level data are accepted or stored.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_principal
from app.db.models import CameraHealthSnapshot, GovernanceAuditEvent, User
from app.db.session import get_db
from app.services.camera_health_engine import CameraHealthMetrics, classify_camera_health
from app.services.camera_ingestion import ingestion_service

router = APIRouter(prefix="/camera-health", tags=["camera-health"])


class CameraHealthIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observed_at: datetime
    last_seen_age_seconds: float = Field(ge=0, le=86400)
    fps: float = Field(ge=0, le=240)
    latency_ms: float = Field(ge=0, le=60000)
    consecutive_missed_heartbeats: int = Field(default=0, ge=0, le=100000)
    reconnect_count: int = Field(default=0, ge=0, le=100000)
    frozen_frame: bool = False
    idempotency_key: str = Field(min_length=8, max_length=128)

    @field_validator("observed_at", mode="before")
    @classmethod
    def require_aware_datetime(cls, value):
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be a timezone-aware datetime")
        return value.astimezone(timezone.utc)

    @field_validator("last_seen_age_seconds", "fps", "latency_ms")
    @classmethod
    def require_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("telemetry values must be finite")
        return value


def _school_id(user: User) -> str:
    if user.role != "principal" or not user.school_id:
        raise HTTPException(status_code=403, detail="A principal assigned to a school is required")
    return user.school_id


def _serialize(row: CameraHealthSnapshot) -> dict[str, object]:
    return {
        "id": row.id,
        "school_id": row.school_id,
        "camera_id": row.camera_id,
        "status": row.status,
        "observed_at": row.observed_at.isoformat(),
        "last_seen_at": row.last_seen_at.isoformat(),
        "fps": row.fps,
        "latency_ms": row.latency_ms,
        "consecutive_missed_heartbeats": row.consecutive_missed_heartbeats,
        "reconnect_count": row.reconnect_count,
        "frozen_frame": row.frozen_frame,
        "source": row.source,
    }


@router.post("/{camera_id}", status_code=status.HTTP_201_CREATED)
def record_camera_health(
    camera_id: str,
    payload: CameraHealthIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_principal),
) -> dict[str, object]:
    """Persist one health observation for a camera registered to this school."""
    school_id = _school_id(user)
    if not any(
        source.camera_id == camera_id and source.school_id == school_id
        for source in ingestion_service.list_sources()
    ):
        raise HTTPException(status_code=404, detail="Camera is not registered for this school")

    metrics = CameraHealthMetrics(
        camera_id=camera_id,
        observed_at=payload.observed_at,
        last_seen_age_seconds=payload.last_seen_age_seconds,
        fps=payload.fps,
        latency_ms=payload.latency_ms,
        consecutive_missed_heartbeats=payload.consecutive_missed_heartbeats,
        reconnect_count=payload.reconnect_count,
        frozen_frame=payload.frozen_frame,
    )
    result = classify_camera_health(metrics)
    row = CameraHealthSnapshot(
        school_id=school_id,
        camera_id=camera_id,
        status=result.status.value,
        observed_at=result.observed_at,
        last_seen_at=result.observed_at - timedelta(seconds=result.last_seen_age_seconds),
        fps=result.fps,
        latency_ms=result.latency_ms,
        consecutive_missed_heartbeats=result.consecutive_missed_heartbeats,
        reconnect_count=result.reconnect_count,
        frozen_frame=result.frozen_frame,
        idempotency_key=payload.idempotency_key,
        source="principal_reported",
        created_by_user_id=user.id,
    )
    db.add(row)
    try:
        db.flush()
        db.add(GovernanceAuditEvent(
            school_id=school_id,
            actor_user_id=user.id,
            event_type="camera_health.snapshot_recorded",
            target_type="camera_health_snapshot",
            target_id=str(row.id),
            details={"camera_id": camera_id, "status": row.status, "source": row.source},
        ))
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(CameraHealthSnapshot).where(
            CameraHealthSnapshot.school_id == school_id,
            CameraHealthSnapshot.idempotency_key == payload.idempotency_key,
        ))
        if existing is None or existing.camera_id != camera_id:
            raise HTTPException(status_code=409, detail="Duplicate idempotency key for this school") from None
        return _serialize(existing)
    return _serialize(row)


@router.get("/{camera_id}")
def camera_health_history(
    camera_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    before_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(require_principal),
) -> dict[str, object]:
    """Return only this school's health history for the requested camera."""
    school_id = _school_id(user)
    statement = select(CameraHealthSnapshot).where(
        CameraHealthSnapshot.school_id == school_id,
        CameraHealthSnapshot.camera_id == camera_id,
    )
    if before_id is not None:
        cursor = db.scalar(select(CameraHealthSnapshot).where(
            CameraHealthSnapshot.id == before_id,
            CameraHealthSnapshot.school_id == school_id,
            CameraHealthSnapshot.camera_id == camera_id,
        ))
        if cursor is None:
            raise HTTPException(status_code=404, detail="Health history cursor not found")
        statement = statement.where(CameraHealthSnapshot.id < before_id)
    rows = db.scalars(statement.order_by(
        CameraHealthSnapshot.id.desc()
    ).limit(limit)).all()
    return {
        "school_id": school_id,
        "camera_id": camera_id,
        "items": [_serialize(row) for row in rows],
        "count": len(rows),
        "next_before_id": rows[-1].id if len(rows) == limit else None,
    }
