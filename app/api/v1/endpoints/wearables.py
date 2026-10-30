"""Authenticated WAI wearable ingestion and school-scoped observation history.

This API stores typed measurements only. It does not diagnose health conditions,
infer emotions, or trigger automated student actions.
"""
from __future__ import annotations

import hashlib
import hmac
import math
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_principal
from app.db import models as orm
from app.db.session import get_db

router = APIRouter(prefix="/wearables", tags=["wearables"])

_CLOCK_SKEW_SECONDS = 300
_SUPPORTED_SCHEMA = "wai.v1"


class WearableObservationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default=_SUPPORTED_SCHEMA, min_length=1, max_length=24)
    observed_at: datetime
    heart_rate_bpm: float | None = Field(default=None, ge=30, le=240)
    hrv_ms: float | None = Field(default=None, ge=0, le=500)
    skin_temperature_c: float | None = Field(default=None, ge=20, le=45)
    movement_activity_score: float | None = Field(default=None, ge=0, le=100)
    eda_us: float | None = Field(default=None, ge=0, le=100)
    battery_level: int | None = Field(default=None, ge=0, le=100)
    idempotency_key: str = Field(min_length=8, max_length=128)

    @field_validator("observed_at", mode="before")
    @classmethod
    def require_aware_timestamp(cls, value):
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be a timezone-aware datetime")
        return value.astimezone(timezone.utc)

    @field_validator(
        "heart_rate_bpm", "hrv_ms", "skin_temperature_c",
        "movement_activity_score", "eda_us",
    )
    @classmethod
    def require_finite_measurements(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("wearable measurements must be finite")
        return value

    @model_validator(mode="after")
    def require_at_least_one_measurement(self):
        measurement_fields = (
            self.heart_rate_bpm, self.hrv_ms, self.skin_temperature_c,
            self.movement_activity_score, self.eda_us,
        )
        if all(value is None for value in measurement_fields):
            raise ValueError("at least one wearable measurement is required")
        return self


def _school_id(user: orm.User) -> str:
    if user.role not in {"principal", "teacher"} or not user.school_id:
        raise HTTPException(status_code=403, detail="An authorised school account is required")
    return user.school_id


def _digest(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _find_bracelet(db: Session, bracelet_id: str, school_id: str) -> orm.Bracelet | None:
    return db.scalar(
        select(orm.Bracelet)
        .join(orm.Student, orm.Student.student_id == orm.Bracelet.student_id)
        .where(
            orm.Bracelet.bracelet_id == bracelet_id,
            orm.Student.school_id == school_id,
            orm.Bracelet.is_active.is_(True),
            orm.Student.is_active.is_(True),
        )
    )


def _serialize(
    row: orm.WearableObservation, *, include_identifiers: bool = True
) -> dict[str, object]:
    result: dict[str, object] = {
        "id": row.id,
        "observed_at": row.observed_at.isoformat(),
        "received_at": row.received_at.isoformat(),
        "schema_version": row.schema_version,
        "heart_rate_bpm": row.heart_rate_bpm,
        "hrv_ms": row.hrv_ms,
        "skin_temperature_c": row.skin_temperature_c,
        "movement_activity_score": row.movement_activity_score,
        "eda_us": row.eda_us,
        "battery_level": row.battery_level,
        "data_status": row.data_status,
        "validation_status": row.validation_status,
    }
    if include_identifiers:
        result.update({
            "school_id": row.school_id,
            "student_id": row.student_id,
            "bracelet_id": row.bracelet_id,
            "device_id": row.device_id,
        })
    return result


@router.post("/devices/{bracelet_id}", status_code=status.HTTP_201_CREATED)
def provision_wearable_device(
    bracelet_id: str,
    db: Session = Depends(get_db),
    user: orm.User = Depends(require_principal),
) -> dict[str, object]:
    """Issue or rotate a bracelet credential; plaintext is returned only once."""
    school_id = _school_id(user)
    bracelet = _find_bracelet(db, bracelet_id, school_id)
    if bracelet is None:
        raise HTTPException(status_code=404, detail="Active bracelet not found for this school")

    device = db.scalar(
        select(orm.WearableEdgeDevice).where(
            orm.WearableEdgeDevice.school_id == school_id,
            orm.WearableEdgeDevice.bracelet_id == bracelet_id,
        )
    )
    if device is not None and device.is_active:
        raise HTTPException(status_code=409, detail="An active wearable identity already exists")
    credential_rotated = device is not None

    secret = secrets.token_urlsafe(32)
    if device is None:
        device = orm.WearableEdgeDevice(
            device_id=str(uuid.uuid4()),
            school_id=school_id,
            bracelet_id=bracelet_id,
            secret_hash=_digest(secret),
            is_active=True,
            provisioned_by_user_id=user.id,
        )
        db.add(device)
    else:
        # Re-provisioning rotates the credential on the existing unique identity.
        device.secret_hash = _digest(secret)
        device.is_active = True
        device.provisioned_by_user_id = user.id
        device.created_at = datetime.now(timezone.utc)
        device.revoked_at = None
    db.add(orm.GovernanceAuditEvent(
        school_id=school_id,
        actor_user_id=user.id,
        event_type="wearable.device_provisioned",
        target_type="wearable_edge_device",
        target_id=device.device_id,
        details={"bracelet_id": bracelet_id, "credential_rotated": credential_rotated},
    ))
    db.commit()
    return {
        "device_id": device.device_id,
        "bracelet_id": bracelet_id,
        "school_id": school_id,
        "device_secret": secret,
        "secret_delivery": "shown_once_store_in_device_secret_store",
    }


@router.post("/devices/{device_id}/revoke")
def revoke_wearable_device(
    device_id: str,
    db: Session = Depends(get_db),
    user: orm.User = Depends(require_principal),
) -> dict[str, object]:
    school_id = _school_id(user)
    device = db.scalar(
        select(orm.WearableEdgeDevice).where(
            orm.WearableEdgeDevice.device_id == device_id,
            orm.WearableEdgeDevice.school_id == school_id,
        )
    )
    if device is None:
        raise HTTPException(status_code=404, detail="Wearable device not found")
    if device.is_active:
        device.is_active = False
        device.revoked_at = datetime.now(timezone.utc)
        db.add(orm.GovernanceAuditEvent(
            school_id=school_id,
            actor_user_id=user.id,
            event_type="wearable.device_revoked",
            target_type="wearable_edge_device",
            target_id=device_id,
            details={"bracelet_id": device.bracelet_id},
        ))
        db.commit()
    return {"device_id": device_id, "is_active": device.is_active}


@router.post("/edge/{device_id}", status_code=status.HTTP_201_CREATED)
def ingest_wearable_observation(
    device_id: str,
    payload: WearableObservationIn,
    x_wearable_device_secret: str | None = Header(default=None, alias="X-Wearable-Device-Secret"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Accept a typed WAI observation from an active device identity."""
    if not x_wearable_device_secret:
        raise HTTPException(status_code=401, detail="Wearable device credentials required")
    device = db.get(orm.WearableEdgeDevice, device_id)
    if device is None or not device.is_active:
        raise HTTPException(status_code=401, detail="Invalid or revoked wearable credentials")
    if not hmac.compare_digest(device.secret_hash, _digest(x_wearable_device_secret)):
        raise HTTPException(status_code=401, detail="Invalid or revoked wearable credentials")
    if payload.schema_version != _SUPPORTED_SCHEMA:
        raise HTTPException(status_code=422, detail="Unsupported wearable schema version")
    now = datetime.now(timezone.utc)
    if abs((now - payload.observed_at).total_seconds()) > _CLOCK_SKEW_SECONDS:
        raise HTTPException(status_code=422, detail="Wearable timestamp is outside the accepted clock-skew window")

    bracelet = _find_bracelet(db, device.bracelet_id, device.school_id)
    if bracelet is None:
        raise HTTPException(status_code=409, detail="Bracelet assignment is no longer active")
    row = orm.WearableObservation(
        school_id=device.school_id,
        student_id=bracelet.student_id,
        bracelet_id=bracelet.bracelet_id,
        device_id=device.device_id,
        observed_at=payload.observed_at,
        schema_version=payload.schema_version,
        heart_rate_bpm=payload.heart_rate_bpm,
        hrv_ms=payload.hrv_ms,
        skin_temperature_c=payload.skin_temperature_c,
        movement_activity_score=payload.movement_activity_score,
        eda_us=payload.eda_us,
        battery_level=payload.battery_level,
        idempotency_key=payload.idempotency_key,
        data_status="live_unverified",
        # Authenticated transport is not proof of hardware capability or signal quality.
        # Keep observations out of live coverage until a supervised hardware-validation flow exists.
        validation_status="pending_hardware_verification",
    )
    device.last_seen_at = now
    if payload.battery_level is not None:
        bracelet.battery_level = payload.battery_level
    bracelet.last_seen_at = now
    db.add(row)
    try:
        db.flush()
        db.add(orm.GovernanceAuditEvent(
            school_id=device.school_id,
            actor_user_id=device.provisioned_by_user_id,
            event_type="wearable.observation_ingested",
            target_type="wearable_observation",
            target_id=str(row.id),
            details={
                "bracelet_id": bracelet.bracelet_id,
                "device_id": device_id,
                "schema_version": payload.schema_version,
                "measurement_fields": [
                    name for name in (
                        "heart_rate_bpm", "hrv_ms", "skin_temperature_c",
                        "movement_activity_score", "eda_us",
                    ) if getattr(payload, name) is not None
                ],
                "data_status": "live_unverified",
                "validation_status": "pending_hardware_verification",
                "coverage_eligible": False,
            },
        ))
        db.commit()
        db.refresh(row)
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(orm.WearableObservation).where(
                orm.WearableObservation.school_id == device.school_id,
                orm.WearableObservation.device_id == device_id,
                orm.WearableObservation.idempotency_key == payload.idempotency_key,
            )
        )
        if existing is None:
            raise HTTPException(status_code=409, detail="Duplicate wearable observation key") from None
        return _serialize(existing, include_identifiers=False)
    return _serialize(row, include_identifiers=False)


@router.get("/overview")
def wearable_school_overview(
    db: Session = Depends(get_db),
    user: orm.User = Depends(require_principal),
) -> dict[str, object]:
    """Expose privacy-preserving school-level reporting coverage, never individual readings."""
    school_id = _school_id(user)
    from app.services.wearable_aggregation import school_wearable_reporting_metrics

    metrics = school_wearable_reporting_metrics(db, school_id)
    available = bool(metrics)
    return {
        "status": "available" if available else "suppressed",
        "coverage_percent": metrics.get("wearable_coverage_percent"),
        "reporting_devices": metrics.get("wearable_reporting_devices"),
        "reporting_window_hours": 24,
        "minimum_cohort_size": 10,
        "message": (
            "School-level device reporting coverage only; individual physiological readings are not shown."
            if available
            else "Coverage is withheld until at least 10 active assigned students have accepted observations from hardware-verified devices within the last 24 hours; pending hardware verification is excluded. Individual physiological readings are not shown."
        ),
        "data_status": "live_unverified",
        "human_review_required": True,
    }


@router.get("/{bracelet_id}/observations")
def wearable_observation_history(
    bracelet_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    before_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    user: orm.User = Depends(require_principal),
) -> dict[str, object]:
    """Return sensitive wearable history to the school principal only, with access audit."""
    school_id = _school_id(user)
    statement = select(orm.WearableObservation).where(
        orm.WearableObservation.school_id == school_id,
        orm.WearableObservation.bracelet_id == bracelet_id,
    )
    if before_id is not None:
        cursor = db.scalar(
            select(orm.WearableObservation).where(
                orm.WearableObservation.id == before_id,
                orm.WearableObservation.school_id == school_id,
                orm.WearableObservation.bracelet_id == bracelet_id,
            )
        )
        if cursor is None:
            raise HTTPException(status_code=404, detail="Wearable history cursor not found")
        statement = statement.where(orm.WearableObservation.id < before_id)
    rows = db.scalars(
        statement.order_by(orm.WearableObservation.id.desc()).limit(limit)
    ).all()
    db.add(orm.GovernanceAuditEvent(
        school_id=school_id,
        actor_user_id=user.id,
        event_type="wearable.history_accessed",
        target_type="wearable_bracelet",
        target_id=bracelet_id,
        details={"returned_count": len(rows), "limit": limit},
    ))
    db.commit()
    return {
        "bracelet_id": bracelet_id,
        "items": [_serialize(row) for row in rows],
        "count": len(rows),
        "next_before_id": rows[-1].id if len(rows) == limit else None,
        "data_status_note": "Device-originated readings remain pending_hardware_verification and are excluded from live coverage until supervised hardware validation is implemented and completed.",
    }
