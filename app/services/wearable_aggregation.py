"""Privacy-preserving school-level WAI device reporting metrics.

Only collection coverage is exposed to the six-agent orchestrator. Individual
wearable measurements (heart rate, HRV, temperature, activity, EDA) are never
queried or passed into the agent pipeline.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import models as orm

_MINIMUM_COHORT_SIZE = 10
_REPORTING_WINDOW = timedelta(hours=24)


def _eligible_observations(db: Session, school_id: str, cutoff: datetime):
    return (
        select(orm.WearableObservation)
        .join(
            orm.WearableEdgeDevice,
            orm.WearableEdgeDevice.device_id == orm.WearableObservation.device_id,
        )
        .join(
            orm.Student,
            orm.Student.student_id == orm.WearableObservation.student_id,
        )
        .join(
            orm.Bracelet,
            orm.Bracelet.bracelet_id == orm.WearableObservation.bracelet_id,
        )
        .where(
            orm.WearableObservation.school_id == school_id,
            orm.WearableEdgeDevice.school_id == school_id,
            orm.WearableEdgeDevice.bracelet_id == orm.WearableObservation.bracelet_id,
            orm.Student.school_id == school_id,
            orm.Student.is_active.is_(True),
            orm.Bracelet.is_active.is_(True),
            orm.WearableObservation.observed_at >= cutoff,
            orm.WearableObservation.validation_status == "accepted",
            orm.WearableObservation.data_status == "live_unverified",
            orm.WearableEdgeDevice.is_active.is_(True),
        )
    )


def school_wearable_reporting_metrics(
    db: Session, school_id: str, *, now: datetime | None = None
) -> dict[str, int | float]:
    """Return school-wide reporting coverage only when at least 10 students report."""
    current = now or datetime.now(timezone.utc)
    cutoff = current - _REPORTING_WINDOW

    assigned_count = db.scalar(
        select(func.count(func.distinct(orm.Bracelet.student_id)))
        .join(orm.Student, orm.Student.student_id == orm.Bracelet.student_id)
        .where(
            orm.Student.school_id == school_id,
            orm.Student.is_active.is_(True),
            orm.Bracelet.is_active.is_(True),
        )
    ) or 0

    eligible = _eligible_observations(db, school_id, cutoff).subquery()
    reporting_students = db.scalar(
        select(func.count(func.distinct(eligible.c.student_id)))
    ) or 0

    if assigned_count < _MINIMUM_COHORT_SIZE or reporting_students < _MINIMUM_COHORT_SIZE:
        return {}

    reporting_devices = db.scalar(
        select(func.count(func.distinct(eligible.c.device_id)))
    ) or 0

    return {
        "wearable_coverage_percent": round(100.0 * reporting_students / assigned_count, 1),
        "wearable_reporting_devices": int(reporting_devices),
    }
