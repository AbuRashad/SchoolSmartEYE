"""Verified, tenant-scoped camera analytics derived only from authenticated edge telemetry."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CameraEdgeDevice, CameraHealthSnapshot

FRESHNESS_SECONDS = 90
_OPERATIONAL_STATUSES = {"online", "degraded"}


def _unavailable() -> dict[str, object]:
    return {"value": None, "status": "unavailable", "source": None, "observed_at": None}


def camera_analytics(
    db: Session,
    *,
    school_id: str | None,
    now: datetime | None = None,
) -> dict[str, dict[str, object]]:
    """Aggregate active provisioned cameras without exposing school/device identities.

    school_id=None is the Ministry-wide read-only aggregate. Only edge_agent
    heartbeats update device last_seen_at; principal-reported snapshots are
    deliberately excluded from these operational metrics.
    """
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    current = current.astimezone(timezone.utc)

    device_query = select(CameraEdgeDevice).where(CameraEdgeDevice.is_active.is_(True))
    if school_id is not None:
        device_query = device_query.where(CameraEdgeDevice.school_id == school_id)
    devices = db.scalars(device_query).all()

    # A device with no authenticated heartbeat has no defensible live status.
    known_devices = [device for device in devices if device.last_seen_at is not None]
    if not known_devices:
        return {
            "active_cameras": _unavailable(),
            "total_units": _unavailable(),
            "uptime_percent": _unavailable(),
        }

    keys = {(device.school_id, device.camera_id) for device in known_devices}
    snapshot_query = select(CameraHealthSnapshot).where(
        CameraHealthSnapshot.source == "edge_agent",
        CameraHealthSnapshot.observed_at >= current - timedelta(seconds=FRESHNESS_SECONDS),
        CameraHealthSnapshot.observed_at <= current + timedelta(seconds=30),
    )
    if school_id is not None:
        snapshot_query = snapshot_query.where(CameraHealthSnapshot.school_id == school_id)
    snapshots = db.scalars(snapshot_query.order_by(CameraHealthSnapshot.observed_at.desc())).all()

    latest: dict[tuple[str, str], CameraHealthSnapshot] = {}
    for snapshot in snapshots:
        key = (snapshot.school_id, snapshot.camera_id)
        if key in keys and key not in latest:
            latest[key] = snapshot

    states: list[str] = []
    observed_times: list[datetime] = []
    for device in known_devices:
        key = (device.school_id, device.camera_id)
        snapshot = latest.get(key)
        # last_seen_at is written only after successful edge credential validation.
        if snapshot is None or device.last_seen_at < current - timedelta(seconds=FRESHNESS_SECONDS):
            states.append("offline")
            continue
        states.append(snapshot.status)
        observed_times.append(snapshot.observed_at)

    total = len(known_devices)
    operational = sum(state in _OPERATIONAL_STATUSES for state in states)
    active_value = operational
    uptime_value = round((operational / total) * 100, 2)
    observed_at = max(observed_times).isoformat() if observed_times else None
    source = "authenticated_edge_agent_telemetry"
    return {
        "active_cameras": {
            "value": active_value, "status": "live", "source": source, "observed_at": observed_at
        },
        "total_units": {
            "value": total, "status": "live", "source": "active_edge_device_registry", "observed_at": observed_at
        },
        "uptime_percent": {
            "value": uptime_value, "status": "live", "source": source, "observed_at": observed_at
        },
    }
