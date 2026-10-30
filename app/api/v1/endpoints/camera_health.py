"""School-scoped persistence and history for camera operational telemetry.

Only principals can submit telemetry in this phase. An authenticated edge-agent
identity and device credential flow must be added before unattended device use.
No frames, images, audio, or person-level data are accepted or stored.
"""
from __future__ import annotations

import hashlib
import hmac
import math
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_principal, require_teacher
from app.db.models import CameraEdgeDevice, CameraHealthSnapshot, GovernanceAuditEvent, User
from app.db.session import get_db
from app.services.camera_health_engine import CameraHealthMetrics, classify_camera_health
from app.services.camera_ingestion import ingestion_service

router = APIRouter(prefix="/camera-health", tags=["camera-health"])\n\n_EDGE_CLOCK_SKEW_SECONDS = 300\n\ndef _secret_digest(secret: str) -> str:\n    return hashlib.sha256(secret.encode("utf-8")).hexdigest()\n\ndef _edge_idempotency_key(device_id: str, key: str) -> str:\n    digest = hashlib.sha256(f"{device_id}:{key}".encode("utf-8")).hexdigest()\n    return f"edge:{digest}"\n\ndef _camera_is_registered(camera_id: str, school_id: str) -> bool:\n    return any(source.camera_id == camera_id and source.school_id == school_id for source in ingestion_service.list_sources())


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


def _school_id(user: User, *, principal_only: bool = True) -> str:
    allowed_roles = {"principal"} if principal_only else {"teacher", "principal"}
    if user.role not in allowed_roles or not user.school_id:
        raise HTTPException(status_code=403, detail="An authorised school account is required")
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
    user: User = Depends(require_teacher),
) -> dict[str, object]:
    """Return only this school's health history for the requested camera."""
    school_id = _school_id(user, principal_only=False)
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



@router.post("/devices/{camera_id}", status_code=status.HTTP_201_CREATED)
def provision_edge_device(
    camera_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_principal),
) -> dict[str, object]:
    """Provision a single edge identity. The plaintext secret is returned once."""
    school_id = _school_id(user)
    if not _camera_is_registered(camera_id, school_id):
        raise HTTPException(status_code=404, detail="Camera is not registered for this school")
    existing = db.scalar(select(CameraEdgeDevice).where(
        CameraEdgeDevice.school_id == school_id,
        CameraEdgeDevice.camera_id == camera_id,
        CameraEdgeDevice.is_active.is_(True),
    ))
    if existing is not None:
        raise HTTPException(status_code=409, detail="An active edge device already exists for this camera")
    device_id = str(uuid.uuid4())
    secret = secrets.token_urlsafe(32)
    device = CameraEdgeDevice(
        device_id=device_id,
        school_id=school_id,
        camera_id=camera_id,
        secret_hash=_secret_digest(secret),
        is_active=True,
        provisioned_by_user_id=user.id,
    )
    db.add(device)
    db.add(GovernanceAuditEvent(
        school_id=school_id,
        actor_user_id=user.id,
        event_type="camera_edge.device_provisioned",
        target_type="camera_edge_device",
        target_id=device_id,
        details={"camera_id": camera_id},
    ))
    db.commit()
    return {
        "device_id": device_id,
        "camera_id": camera_id,
        "school_id": school_id,
        "device_secret": secret,
        "secret_delivery": "shown_once_store_in_edge_agent_secret_store",
    }


@router.post("/devices/{device_id}/revoke")
def revoke_edge_device(
    device_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_principal),
) -> dict[str, object]:
    school_id = _school_id(user)
    device = db.scalar(select(CameraEdgeDevice).where(
        CameraEdgeDevice.device_id == device_id,
        CameraEdgeDevice.school_id == school_id,
    ))
    if device is None:
        raise HTTPException(status_code=404, detail="Edge device not found")
    if device.is_active:
        device.is_active = False
        device.revoked_at = datetime.now(timezone.utc)
        db.add(GovernanceAuditEvent(
            school_id=school_id,
            actor_user_id=user.id,
            event_type="camera_edge.device_revoked",
            target_type="camera_edge_device",
            target_id=device_id,
            details={"camera_id": device.camera_id},
        ))
        db.commit()
    return {"device_id": device_id, "is_active": device.is_active, "revoked_at": device.revoked_at.isoformat() if device.revoked_at else None}


@router.post("/edge/{device_id}", status_code=status.HTTP_201_CREATED)
def record_edge_heartbeat(
    device_id: str,
    payload: CameraHealthIn,
    x_edge_device_secret: str | None = Header(default=None, alias="X-Edge-Device-Secret"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Accept health telemetry only from an active, provisioned edge identity."""
    if not x_edge_device_secret:
        raise HTTPException(status_code=401, detail="Edge device credentials required")
    device = db.get(CameraEdgeDevice, device_id)
    if device is None or not device.is_active:
        raise HTTPException(status_code=401, detail="Invalid or revoked edge credentials")
    supplied_digest = _secret_digest(x_edge_device_secret)
    if not hmac.compare_digest(device.secret_hash, supplied_digest):
        raise HTTPException(status_code=401, detail="Invalid or revoked edge credentials")
    if not _camera_is_registered(device.camera_id, device.school_id):
        raise HTTPException(status_code=409, detail="Provisioned camera is no longer registered")
    now = datetime.now(timezone.utc)
    if abs((now - payload.observed_at).total_seconds()) > _EDGE_CLOCK_SKEW_SECONDS:
        raise HTTPException(status_code=422, detail="Edge timestamp is outside the accepted clock-skew window")

    metrics = CameraHealthMetrics(
        camera_id=device.camera_id,
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
        school_id=device.school_id,
        camera_id=device.camera_id,
        status=result.status.value,
        observed_at=result.observed_at,
        last_seen_at=result.observed_at - timedelta(seconds=result.last_seen_age_seconds),
        fps=result.fps,
        latency_ms=result.latency_ms,
        consecutive_missed_heartbeats=result.consecutive_missed_heartbeats,
        reconnect_count=result.reconnect_count,
        frozen_frame=result.frozen_frame,
        idempotency_key=_edge_idempotency_key(device_id, payload.idempotency_key),
        source="edge_agent",
        created_by_user_id=device.provisioned_by_user_id,
    )
    device.last_seen_at = now
    db.add(row)
    try:
        db.flush()
        db.add(GovernanceAuditEvent(
            school_id=device.school_id,
            actor_user_id=device.provisioned_by_user_id,
            event_type="camera_edge.heartbeat_recorded",
            target_type="camera_health_snapshot",
            target_id=str(row.id),
            details={"camera_id": device.camera_id, "status": row.status, "device_id": device_id},
        ))
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(CameraHealthSnapshot).where(
            CameraHealthSnapshot.school_id == device.school_id,
            CameraHealthSnapshot.idempotency_key == _edge_idempotency_key(device_id, payload.idempotency_key),
        ))
        if existing is None:
            raise HTTPException(status_code=409, detail="Duplicate heartbeat key") from None
        return _serialize(existing)
    return _serialize(row)
