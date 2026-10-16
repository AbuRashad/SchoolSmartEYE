"""Persisted School Safety Index history: recording, trends and anomaly detection."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import fmean, pstdev

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models as orm

TREND_SLOPE_THRESHOLD = 0.1  # SSI points per day treated as a real trend
ANOMALY_Z_THRESHOLD = 2.0


def record_snapshot(
    db: Session,
    ssi: float,
    *,
    anomaly_coefficient: float | None = None,
    coherence_score: float | None = None,
    attendance_discrepancy: float | None = None,
    predicted_density: float | None = None,
    source: str = "live",
    recorded_at: datetime | None = None,
) -> orm.SSISnapshot:
    snap = orm.SSISnapshot(
        recorded_at=recorded_at or datetime.now(timezone.utc),
        ssi=float(ssi),
        anomaly_coefficient=anomaly_coefficient,
        coherence_score=coherence_score,
        attendance_discrepancy=attendance_discrepancy,
        predicted_density=predicted_density,
        source=source,
    )
    db.add(snap)
    db.commit()
    return snap


def record_if_due(db: Session, ssi: float, min_interval_seconds: int = 300, **kwargs) -> bool:  # noqa: ANN003
    """Record a live snapshot unless one was stored recently (bounds writes from polling)."""
    last = db.scalar(select(orm.SSISnapshot)
        .where(orm.SSISnapshot.source == kwargs.get("source", "live"))
        .order_by(orm.SSISnapshot.recorded_at.desc())
        .limit(1))
    if last is not None and (datetime.now(timezone.utc) - last.recorded_at).total_seconds() < min_interval_seconds:
        return False
    record_snapshot(db, ssi, **kwargs)
    return True


def get_history(db: Session, days: int = 30) -> list[orm.SSISnapshot]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    return list(
        db.scalars(
            select(orm.SSISnapshot)
            .where(orm.SSISnapshot.recorded_at >= since)
            .order_by(orm.SSISnapshot.recorded_at)
        )
    )


def _slope(values: list[float]) -> float:
    """Least-squares slope per step."""
    n = len(values)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2
    mean_y = fmean(values)
    den = sum((i - mean_x) ** 2 for i in range(n))
    return sum((i - mean_x) * (v - mean_y) for i, v in enumerate(values)) / den


def daily_series(snapshots: list[orm.SSISnapshot]) -> list[tuple[str, float]]:
    """Average SSI per UTC calendar day, oldest first."""
    buckets: dict[str, list[float]] = {}
    for s in snapshots:
        buckets.setdefault(s.recorded_at.date().isoformat(), []).append(s.ssi)
    return [(d, fmean(v)) for d, v in sorted(buckets.items())]


def compute_trend(daily: list[tuple[str, float]]) -> dict[str, object]:
    values = [v for _, v in daily]
    if len(values) < 3:
        return {"direction": "insufficient_data", "slope_per_day": 0.0, "points": len(values)}
    slope = _slope(values)
    if slope > TREND_SLOPE_THRESHOLD:
        direction = "improving"
    elif slope < -TREND_SLOPE_THRESHOLD:
        direction = "declining"
    else:
        direction = "stable"
    return {"direction": direction, "slope_per_day": round(slope, 4), "points": len(values)}


def detect_anomalies(
    daily: list[tuple[str, float]], z_threshold: float = ANOMALY_Z_THRESHOLD
) -> list[dict[str, object]]:
    """Days whose SSI deviates more than `z_threshold` std-devs from the period mean."""
    values = [v for _, v in daily]
    if len(values) < 5:
        return []
    mean, sd = fmean(values), pstdev(values)
    if sd == 0:
        return []
    return [
        {"date": d, "ssi": round(v, 2), "z_score": round((v - mean) / sd, 2)}
        for d, v in daily
        if abs(v - mean) / sd >= z_threshold
    ]


def summarize(db: Session, days: int = 30) -> dict[str, object]:
    snaps = get_history(db, days)
    daily = daily_series(snaps)
    trend = compute_trend(daily)
    values = [v for _, v in daily]
    return {
        "scores": [{"day": i + 1, "date": d, "ssi": round(v, 2)} for i, (d, v) in enumerate(daily)],
        "average": round(fmean(values), 2) if values else None,
        "trend": trend["direction"],
        "trend_detail": trend,
        "anomalies": detect_anomalies(daily),
        "snapshots": len(snaps),
    }
