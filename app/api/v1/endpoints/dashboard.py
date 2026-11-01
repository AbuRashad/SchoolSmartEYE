"""Database-backed dashboard endpoints scoped to the authenticated school.

The REST views below use persisted school-owned records only. The WebSocket
stream remains disabled until the broadcaster itself is tenant-partitioned.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    _check_roles,
    _user_from_token,
    get_current_school_id,
    require_teacher,
    resolve_school_scope,
)
from app.core.governance_layer import Role
from app.db import models as orm
from app.db.session import SessionLocal, get_db
from app.services import seed_data

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _summary(db: Session, school_id: str) -> dict[str, object]:
    school = db.get(orm.School, school_id)
    if school is None or not school.is_active:
        raise HTTPException(status_code=404, detail="School not found")
    metrics = seed_data.get_school_metrics(db, school_id)
    latest_ssi = db.scalar(
        select(orm.SSISnapshot.ssi)
        .where(orm.SSISnapshot.school_id == school_id)
        .order_by(orm.SSISnapshot.recorded_at.desc())
        .limit(1)
    )
    return {
        "schoolName": school.name,
        "schoolId": school_id,
        "totalStudents": metrics.total_students,
        "presentToday": metrics.present_today,
        "attendanceRate": metrics.attendance_rate,
        "activeCameras": metrics.active_cameras,
        "openIncidents": metrics.open_incidents,
        "ssi": latest_ssi,
        "ssiStatus": "measured" if latest_ssi is not None else "awaiting_school_measurement",
        "benchmark": 75.0,
        "computedAt": metrics.computed_at.isoformat(),
        "dataSource": "school_scoped_database",
        "websocketStatus": "disabled_until_tenant_partitioned",
    }


def _alerts(db: Session, school_id: str) -> list[dict[str, object]]:
    rows = db.execute(
        select(orm.Incident, orm.Zone.label)
        .join(orm.Zone, orm.Zone.zone_id == orm.Incident.zone_id)
        .where(orm.Zone.school_id == school_id, orm.Incident.resolved.is_(False))
        .order_by(orm.Incident.detected_at.desc())
        .limit(100)
    ).all()
    return [
        {
            "id": incident.incident_id,
            "title": f"{incident.severity.title()} incident — {zone_label}",
            "message": incident.description,
            "severity": incident.severity,
            "stream": "persisted_incident",
            "zoneId": incident.zone_id,
            "zoneLabel": zone_label,
            "computed_at": incident.detected_at.isoformat(),
        }
        for incident, zone_label in rows
    ]


def _heatmap(db: Session, school_id: str) -> dict[str, object]:
    zones = db.scalars(
        select(orm.Zone).where(orm.Zone.school_id == school_id)
        .order_by(orm.Zone.floor, orm.Zone.grid_y, orm.Zone.grid_x)
    ).all()
    incidents = db.execute(
        select(orm.Incident.zone_id, orm.Incident.severity)
        .join(orm.Zone, orm.Zone.zone_id == orm.Incident.zone_id)
        .where(orm.Zone.school_id == school_id, orm.Incident.resolved.is_(False))
    ).all()
    weights = {"low": 0.2, "medium": 0.4, "high": 0.7, "critical": 1.0}
    by_zone: dict[str, list[float]] = {}
    for zone_id, severity in incidents:
        by_zone.setdefault(zone_id, []).append(weights.get(severity, 0.0))
    cells = []
    for zone in zones:
        signals = by_zone.get(zone.zone_id, [])
        cells.append({
            "zone_id": zone.zone_id,
            "label": zone.label,
            "floor": zone.floor,
            "x": zone.grid_x,
            "y": zone.grid_y,
            "risk_intensity": round(min(1.0, sum(signals)), 3),
            "open_incidents": len(signals),
            "signal_source": "persisted_open_incidents",
        })
    return {
        "school_id": school_id,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "cells": cells,
        "availableTimeSlots": ["current"],
        "dataSource": "school_scoped_database",
        "interpretation": "Incident signal only; not a camera-derived or predictive risk score.",
    }


@router.get("/summary", dependencies=[Depends(require_teacher)])
def dashboard_summary(
    db: Session = Depends(get_db), school_id: str = Depends(get_current_school_id)
) -> dict[str, object]:
    return _summary(db, school_id)


@router.get("/alerts", dependencies=[Depends(require_teacher)])
def dashboard_alerts(
    db: Session = Depends(get_db), school_id: str = Depends(get_current_school_id)
) -> list[dict[str, object]]:
    return _alerts(db, school_id)


@router.get("/heatmap", dependencies=[Depends(require_teacher)])
def dashboard_heatmap(
    db: Session = Depends(get_db), school_id: str = Depends(get_current_school_id)
) -> dict[str, object]:
    return _heatmap(db, school_id)


@router.get("/live", dependencies=[Depends(require_teacher)])
def dashboard_live(
    db: Session = Depends(get_db), school_id: str = Depends(get_current_school_id)
) -> dict[str, object]:
    return {
        **_summary(db, school_id),
        "liveAlerts": _alerts(db, school_id),
        **{ "heatmap": _heatmap(db, school_id) },
        "fetchedFromBackend": True,
        "snapshotType": "database_derived_not_streaming",
    }


@router.websocket("/ws")
async def dashboard_ws(websocket: WebSocket, access_token: str | None = Query(default=None)) -> None:
    # The former process-global broadcaster could send the same snapshot to all schools.
    try:
        with SessionLocal() as db:
            user = _user_from_token(access_token, db)
            _check_roles(user, (Role.TEACHER,))
            resolve_school_scope(db, user)
    except HTTPException as exc:
        await websocket.close(code=4401 if exc.status_code == 401 else 4403)
        return
    await websocket.close(code=1013, reason="School-scoped WebSocket broadcaster is not available yet")
