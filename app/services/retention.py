"""Retention services for timestamped bracelet telemetry."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models as orm


def bracelet_reading_cutoff(now: datetime | None = None) -> datetime:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc) - timedelta(days=settings.bracelet_reading_retention_days)


def purge_expired_bracelet_readings(
    db: Session, *, now: datetime | None = None
) -> int:
    """Hard-delete readings older than the configured retention window."""
    result = db.execute(
        delete(orm.BraceletReading).where(
            orm.BraceletReading.recorded_at < bracelet_reading_cutoff(now)
        )
    )
    db.commit()
    return int(result.rowcount or 0)
