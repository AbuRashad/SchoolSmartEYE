"""Principal-authorised ingestion of privacy-minimised aggregate observations."""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_principal
from app.db.models import AggregateObservation, GovernanceAuditEvent, User
from app.db.session import get_db

router = APIRouter(prefix="/observations", tags=["observations"])

# Explicit allowlist: only school-level aggregates; no student identifiers or free text.
METRIC_RANGES: dict[str, tuple[float, float]] = {
    "attendance_rate": (0.0, 100.0),
    "incident_count": (0.0, 10000.0),
    "crowd_density": (0.0, 1.0),
    "ssi": (0.0, 100.0),
    "camera_uptime": (0.0, 100.0),
    "drill_response_seconds": (0.0, 86400.0),
}


class ObservationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_key: str = Field(min_length=1, max_length=80)
    metric_value: float
    observed_at: datetime
    source_id: str = Field(min_length=1, max_length=120)
    idempotency_key: str = Field(min_length=8, max_length=128)
    metric_version: Literal["1"] = "1"

    @field_validator("observed_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone")
        return value.astimezone(timezone.utc)

    @field_validator("metric_value")
    @classmethod
    def require_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("metric_value must be finite")
        return value


@router.post("", status_code=status.HTTP_201_CREATED)
def ingest_observation(
    payload: ObservationIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_principal),
) -> dict[str, object]:
    """Persist an unverified aggregate; verification is a separate governed action."""
    # This endpoint is school-operated in phase one: Ministry accounts are not school principals.
    if user.role != "principal":
        raise HTTPException(status_code=403, detail="Only the assigned school principal may ingest observations")
    if not user.school_id:
        raise HTTPException(status_code=403, detail="This account is not assigned to a school")
    allowed_range = METRIC_RANGES.get(payload.metric_key)
    if allowed_range is None:
        raise HTTPException(status_code=422, detail="Unsupported aggregate metric")
    if not allowed_range[0] <= payload.metric_value <= allowed_range[1]:
        raise HTTPException(status_code=422, detail="Metric value is outside its permitted range")

    record = AggregateObservation(
        school_id=user.school_id,
        metric_key=payload.metric_key,
        metric_value=payload.metric_value,
        observed_at=payload.observed_at,
        source_id=payload.source_id,
        data_status="live_unverified",
        validation_status="pending",
        metric_version=payload.metric_version,
        idempotency_key=payload.idempotency_key,
        created_by_user_id=user.id,
    )
    db.add(record)
    try:
        # Keep the ingestion record and its audit event in one atomic transaction.
        db.flush()
        db.add(GovernanceAuditEvent(
            school_id=user.school_id,
            actor_user_id=user.id,
            event_type="observation.ingested",
            target_type="aggregate_observation",
            target_id=str(record.id),
            details={
                "metric_key": record.metric_key,
                "source_id": record.source_id,
                "data_status": record.data_status,
                "validation_status": record.validation_status,
            },
        ))
        db.commit()
        db.refresh(record)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate idempotency key for this school") from None

    return {
        "id": record.id,
        "school_id": record.school_id,
        "metric_key": record.metric_key,
        "metric_value": record.metric_value,
        "observed_at": record.observed_at.isoformat(),
        "data_status": record.data_status,
        "validation_status": record.validation_status,
        "message": "Stored for review; this observation is not yet eligible for learning.",
    }
