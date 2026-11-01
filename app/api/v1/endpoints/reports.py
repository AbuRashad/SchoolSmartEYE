"""On-demand school-scoped report previews built from persisted SQL records.

These are generated summaries, not stored downloadable report artifacts.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_school_id, require_ministry
from app.db import models as orm
from app.db.session import get_db
from app.services import ssi_history

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_ministry)])


def _report_previews(db: Session, school_id: str) -> list[dict[str, object]]:
    today = datetime.now(timezone.utc).date()
    attendance_rows = db.execute(
        select(orm.AttendanceRecord.status, func.count())
        .join(orm.Student, orm.Student.student_id == orm.AttendanceRecord.student_id)
        .where(orm.Student.school_id == school_id, orm.AttendanceRecord.date == today)
        .group_by(orm.AttendanceRecord.status)
    ).all()
    attendance = {status: int(count) for status, count in attendance_rows}
    incident_rows = db.execute(
        select(orm.Incident.severity, func.count())
        .join(orm.Zone, orm.Zone.zone_id == orm.Incident.zone_id)
        .where(orm.Zone.school_id == school_id, orm.Incident.resolved.is_(False))
        .group_by(orm.Incident.severity)
    ).all()
    incidents = {severity: int(count) for severity, count in incident_rows}
    total_students = db.scalar(
        select(func.count()).select_from(orm.Student).where(
            orm.Student.school_id == school_id, orm.Student.is_active.is_(True)
        )
    ) or 0
    ssi = ssi_history.summarize(db, school_id, 30)
    generated_at = datetime.now(timezone.utc).isoformat()
    data_status = "demo" if school_id == "DEMO-SCHOOL-001" else "unknown"
    data_notice = (
        "Synthetic demo seed data; not live school telemetry."
        if data_status == "demo"
        else "School isolation is enforced, but record-level source provenance has not been verified."
    )

    return [
        {
            "report_id": f"{school_id}:attendance:{today.isoformat()}",
            "title": "Daily Attendance Snapshot",
            "report_type": "operational",
            "period_label": today.isoformat(),
            "generated_at": generated_at,
            "is_ready": True,
            "content_summary": (
                f"{sum(attendance.values())} attendance records: "
                f"{attendance.get('present', 0)} present, {attendance.get('late', 0)} late, "
                f"{attendance.get('absent', 0)} absent; {total_students} active students."
            ),
            "data": {"attendance_by_status": attendance, "active_students": int(total_students)},
            "persisted": False,
            "data_status": data_status,
            "data_notice": data_notice,
        },
        {
            "report_id": f"{school_id}:incidents:{today.isoformat()}",
            "title": "Open Safety Incident Summary",
            "report_type": "analytical",
            "period_label": "Current open incidents",
            "generated_at": generated_at,
            "is_ready": True,
            "content_summary": f"{sum(incidents.values())} open incidents across the school's zones.",
            "data": {"open_incidents_by_severity": incidents},
            "persisted": False,
            "data_status": data_status,
            "data_notice": data_notice,
        },
        {
            "report_id": f"{school_id}:ssi:30d",
            "title": "School Safety Index History",
            "report_type": "supervisory",
            "period_label": "Last 30 days",
            "generated_at": generated_at,
            "is_ready": bool(ssi["snapshots"]),
            "content_summary": (
                f"{ssi['snapshots']} school-owned SSI snapshots available."
                if ssi["snapshots"] else "No school-owned SSI history is available yet."
            ),
            "data": ssi,
            "persisted": False,
            "data_status": data_status,
            "data_notice": data_notice,
        },
    ]


@router.get("/list")
def list_reports(
    db: Session = Depends(get_db), school_id: str = Depends(get_current_school_id)
) -> list[dict[str, object]]:
    """Generate report previews from the authenticated school's records."""
    return _report_previews(db, school_id)


@router.get("/stats")
def report_stats(
    db: Session = Depends(get_db), school_id: str = Depends(get_current_school_id)
) -> dict[str, object]:
    reports = _report_previews(db, school_id)
    return {
        "school_id": school_id,
        "total": len(reports),
        "ready": sum(1 for report in reports if report["is_ready"]),
        "pending": sum(1 for report in reports if not report["is_ready"]),
        "generated_on_request": True,
        "stored_artifacts": False,
    }
