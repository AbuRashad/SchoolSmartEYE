"""School-scoped operational analytics from persisted records."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_school_id, require_teacher
from app.db import models as orm
from app.db.session import get_db
from app.services import ssi_history

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(require_teacher)])


@router.get("/overview")
def analytics_overview(
    db: Session = Depends(get_db), school_id: str = Depends(get_current_school_id)
) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=30)
    attendance_rows = db.execute(
        select(orm.AttendanceRecord.date, orm.AttendanceRecord.status, func.count())
        .join(orm.Student, orm.Student.student_id == orm.AttendanceRecord.student_id)
        .where(orm.Student.school_id == school_id, orm.AttendanceRecord.date >= since.date())
        .group_by(orm.AttendanceRecord.date, orm.AttendanceRecord.status)
        .order_by(orm.AttendanceRecord.date)
    ).all()
    attendance_by_day: dict[str, dict[str, int]] = {}
    for day, status_value, count in attendance_rows:
        attendance_by_day.setdefault(day.isoformat(), {})[status_value] = int(count)

    incident_rows = db.execute(
        select(orm.Incident.severity, func.count())
        .join(orm.Zone, orm.Zone.zone_id == orm.Incident.zone_id)
        .where(orm.Zone.school_id == school_id, orm.Incident.detected_at >= since)
        .group_by(orm.Incident.severity)
    ).all()
    incident_by_severity = {severity: int(count) for severity, count in incident_rows}

    total_students = db.scalar(
        select(func.count()).select_from(orm.Student).where(
            orm.Student.school_id == school_id, orm.Student.is_active.is_(True)
        )
    ) or 0
    active_cameras = db.scalar(
        select(func.count()).select_from(orm.Camera)
        .join(orm.Zone, orm.Zone.zone_id == orm.Camera.zone_id)
        .where(orm.Zone.school_id == school_id, orm.Camera.is_active.is_(True))
    ) or 0
    open_incidents = db.scalar(
        select(func.count()).select_from(orm.Incident)
        .join(orm.Zone, orm.Zone.zone_id == orm.Incident.zone_id)
        .where(orm.Zone.school_id == school_id, orm.Incident.resolved.is_(False))
    ) or 0
    incidents_today = db.scalar(
        select(func.count()).select_from(orm.Incident)
        .join(orm.Zone, orm.Zone.zone_id == orm.Incident.zone_id)
        .where(
            orm.Zone.school_id == school_id,
            orm.Incident.detected_at >= datetime.combine(now.date(), datetime.min.time(), tzinfo=timezone.utc),
        )
    ) or 0
    incidents_last_7_days = db.scalar(
        select(func.count()).select_from(orm.Incident)
        .join(orm.Zone, orm.Zone.zone_id == orm.Incident.zone_id)
        .where(
            orm.Zone.school_id == school_id,
            orm.Incident.detected_at >= now - timedelta(days=7),
        )
    ) or 0

    daily = []
    for day, statuses in sorted(attendance_by_day.items()):
        present = statuses.get("present", 0) + statuses.get("late", 0)
        recorded = sum(statuses.values())
        daily.append({
            "date": day,
            "present_or_late": present,
            "absent": statuses.get("absent", 0),
            "recorded": recorded,
            "attendance_rate": round(present / recorded * 100, 1) if recorded else None,
        })

    data_status = "demo" if school_id == "DEMO-SCHOOL-001" else "unknown"
    data_notice = (
        "Synthetic demo seed data; not live school telemetry."
        if data_status == "demo"
        else "School isolation is enforced, but record-level source provenance has not been verified."
    )
    return {
        "school_id": school_id,
        "generated_at": now.isoformat(),
        "period_days": 30,
        "data_source": "school_scoped_database",
        "data_status": data_status,
        "data_notice": data_notice,
        "students": {"active": int(total_students)},
        "cameras": {"active": int(active_cameras)},
        "incidents": {
            "open": int(open_incidents),
            "today": int(incidents_today),
            "last_7_days": int(incidents_last_7_days),
            "last_30_days_by_severity": incident_by_severity,
        },
        "attendance": {
            "daily": daily,
            "note": "Rates use recorded attendance rows only; missing records are not assumed present or absent.",
        },
        "ssi_history": ssi_history.summarize(db, school_id, 30),
    }
