"""Students & zones CRUD used by the Control Panel.

Students, bracelets, attendance and notifications are stored in the SQL
database (see `app.db`); zones and incidents are still in-memory demo data.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_school_principal, require_teacher, school_scope
from app.db import models as orm
from app.db.session import get_db
from app.models import (
    AttendanceStatus,
    IncidentSeverity,
    SafetyStatus,
)
from app.services import seed_data
from app.services.pedagogical_agent import PedagogicalAgentService

router = APIRouter(tags=["control"])

# Lazy singleton for the pedagogical agent service (backed by seed_data stores)
_agent: PedagogicalAgentService | None = None


def _get_agent() -> PedagogicalAgentService:
    global _agent  # noqa: PLW0603
    if _agent is None:
        from app.core.config import settings
        _agent = PedagogicalAgentService(
            snapshots=seed_data.engagement_snapshots,
            feedback_log=[],  # profile only reads engagement snapshots
            video_log_dir=settings.video_log_dir,
        )
    return _agent


# ── Schemas ───────────────────────────────────────────────────────────────────


class StudentOut(BaseModel):
    student_id: str
    name: str
    grade: str
    class_section: str
    parent_id: str
    photo_initial: str
    is_active: bool


class StudentCreate(BaseModel):
    student_id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=128)
    grade: str = Field(..., min_length=1, max_length=64)
    class_section: str = Field(..., min_length=1, max_length=32)
    parent_id: str = Field(..., min_length=1, max_length=64)
    photo_initial: str = Field(default="", max_length=4)
    is_active: bool = Field(default=True)


class StudentUpdate(BaseModel):
    name: str | None = None
    grade: str | None = None
    class_section: str | None = None
    parent_id: str | None = None
    photo_initial: str | None = None
    is_active: bool | None = None


class ZoneOut(BaseModel):
    zone_id: str
    label: str
    zone_type: str
    capacity: int
    floor: int


class BraceletSummary(BaseModel):
    bracelet_id: str
    mac_address: str
    battery_level: int
    is_active: bool
    last_seen_zone: str | None
    last_seen_zone_label: str | None
    last_seen_at: str | None
    firmware_version: str
    notes: str
    low_battery: bool


class AttendanceDay(BaseModel):
    date: str
    status: str
    arrival_time: str | None
    departure_time: str | None
    last_seen_zone: str | None
    last_seen_zone_label: str | None


class NotificationItem(BaseModel):
    notification_id: str
    message: str
    notification_type: str
    sent_at: str
    read: bool


class EngagementSummary(BaseModel):
    avg_score_7d: float
    dominant_state: str
    trend: str
    total_snapshots_7d: int
    mismatch_count_7d: int


class EngagementSnapshotOut(BaseModel):
    student_id: str
    recorded_at: str
    state: str
    score: float
    session_id: str
    zone_id: str | None
    audio_context: str | None
    audio_visual_mismatch: bool


class StudentProfile(BaseModel):
    # Core
    student_id: str
    name: str
    grade: str
    class_section: str
    parent_id: str
    photo_initial: str
    is_active: bool

    # Derived / aggregated
    safety_status: str  # "safe" | "warning" | "critical" | "unknown"
    today_status: str   # "present" | "absent" | "late" | "unknown"
    arrival_time: str | None
    departure_time: str | None
    last_seen_zone: str | None
    last_seen_zone_label: str | None

    attendance_streak: int
    monthly_attendance_pct: float
    last_30_days_present: int
    last_30_days_total: int

    weekly_attendance: list[AttendanceDay]
    recent_attendance: list[AttendanceDay]  # last 30 days

    bracelet: BraceletSummary | None
    notifications: list[NotificationItem]
    unread_notifications: int

    open_incidents_in_last_zone: int

    engagement_summary: EngagementSummary | None


# ── Helpers ───────────────────────────────────────────────────────────────────


def _serialize(s: orm.Student) -> StudentOut:
    return StudentOut(
        student_id=s.student_id,
        name=s.name,
        grade=s.grade,
        class_section=s.class_section,
        parent_id=s.parent_id,
        photo_initial=s.photo_initial,
        is_active=s.is_active,
    )


def _find_student(db: Session, student_id: str, scope: str | None) -> orm.Student | None:
    stmt = select(orm.Student).where(orm.Student.student_id == student_id)
    if scope is not None:
        stmt = stmt.where(orm.Student.school_id == scope)
    return db.scalar(stmt)


# ── Students ──────────────────────────────────────────────────────────────────


@router.get("/students", response_model=list[StudentOut])
def list_students(
    db: Session = Depends(get_db), user: orm.User = Depends(require_teacher)
) -> list[StudentOut]:
    stmt = select(orm.Student).order_by(orm.Student.student_id)
    scope = school_scope(user)
    if scope is not None:
        stmt = stmt.where(orm.Student.school_id == scope)
    rows = db.scalars(stmt).all()
    return [_serialize(s) for s in rows]


@router.post(
    "/students",
    response_model=StudentOut,
    status_code=status.HTTP_201_CREATED,
 )
def create_student(
    payload: StudentCreate,
    db: Session = Depends(get_db),
    user: orm.User = Depends(require_school_principal),
) -> StudentOut:
    school_id = school_scope(user)
    if _find_student(db, payload.student_id, school_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Student {payload.student_id!r} already exists",
        )
    initial = payload.photo_initial or (payload.name[:1].upper() if payload.name else "?")
    student = orm.Student(
        student_id=payload.student_id,
        school_id=school_id,
        name=payload.name,
        grade=payload.grade,
        class_section=payload.class_section,
        parent_id=payload.parent_id,
        photo_initial=initial,
        is_active=payload.is_active,
    )
    db.add(student)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Student {payload.student_id!r} already exists",
        ) from None
    return _serialize(student)


@router.patch("/students/{student_id}", response_model=StudentOut)
def update_student(
    student_id: str,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    user: orm.User = Depends(require_school_principal),
) -> StudentOut:
    student = _find_student(db, student_id, school_scope(user))
    if student is None:
        raise HTTPException(status_code=404, detail=f"Student {student_id!r} not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(student, field, value)
    db.commit()
    return _serialize(student)


@router.delete(
    "/students/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
 )
def delete_student(
    student_id: str,
    db: Session = Depends(get_db),
    user: orm.User = Depends(require_school_principal),
) -> Response:
    student = _find_student(db, student_id, school_scope(user))
    if student is None:
        raise HTTPException(status_code=404, detail=f"Student {student_id!r} not found")
    # Cascade: the student's bracelet and attendance records are removed too
    db.delete(student)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Zones (read-only) ─────────────────────────────────────────────────────────


@router.get("/zones", response_model=list[ZoneOut], dependencies=[Depends(require_teacher)])
def list_zones(db: Session = Depends(get_db)) -> list[ZoneOut]:
    return [
        ZoneOut(
            zone_id=z.zone_id,
            label=z.label,
            zone_type=z.zone_type,
            capacity=z.capacity,
            floor=z.floor,
        )
        for z in db.scalars(select(orm.Zone).order_by(orm.Zone.grid_x, orm.Zone.grid_y))
    ]


# ── Aggregated Student Profile ────────────────────────────────────────────────


_PRESENT_STATUSES = (AttendanceStatus.PRESENT.value, AttendanceStatus.LATE.value)


def _zone_label(db: Session, zone_id: str | None) -> str | None:
    if not zone_id:
        return None
    zone_labels = db.info.get("zone_label_map")
    if zone_labels is None:
        zone_labels = {
            zone.zone_id: zone.label for zone in db.scalars(select(orm.Zone))
        }
        db.info["zone_label_map"] = zone_labels
    return zone_labels.get(zone_id, zone_id)


def _bracelet_summary(db: Session, bracelet: orm.Bracelet | None) -> BraceletSummary | None:
    if bracelet is None:
        return None
    from app.core.runtime_settings import get_runtime_settings
    threshold = get_runtime_settings().bracelet_low_battery_percent
    return BraceletSummary(
        bracelet_id=bracelet.bracelet_id,
        mac_address=bracelet.mac_address,
        battery_level=bracelet.battery_level,
        is_active=bracelet.is_active,
        last_seen_zone=bracelet.last_seen_zone,
        last_seen_zone_label=_zone_label(db, bracelet.last_seen_zone),
        last_seen_at=bracelet.last_seen_at.isoformat() if bracelet.last_seen_at else None,
        firmware_version=bracelet.firmware_version,
        notes=bracelet.notes,
        low_battery=bracelet.battery_level <= threshold,
    )


def _to_attendance_day(db: Session, rec: orm.AttendanceRecord | None, day: date) -> AttendanceDay:
    if rec is None:
        return AttendanceDay(
            date=day.isoformat(),
            status=AttendanceStatus.UNKNOWN.value,
            arrival_time=None,
            departure_time=None,
            last_seen_zone=None,
            last_seen_zone_label=None,
        )
    return AttendanceDay(
        date=day.isoformat(),
        status=rec.status,
        arrival_time=rec.arrival_time.isoformat() if rec.arrival_time else None,
        departure_time=rec.departure_time.isoformat() if rec.departure_time else None,
        last_seen_zone=rec.last_seen_zone,
        last_seen_zone_label=_zone_label(db, rec.last_seen_zone),
    )


def _compute_streak(records_by_date: dict[date, orm.AttendanceRecord], today: date) -> int:
    streak = 0
    cursor = today
    for _ in range(365):  # safety cap
        rec = records_by_date.get(cursor)
        if rec and rec.status in _PRESENT_STATUSES:
            streak += 1
            cursor = cursor - timedelta(days=1)
        else:
            break
    return streak


def _safety_status_for(db: Session, student: orm.Student, last_zone: str | None) -> str:
    if not student.is_active:
        return SafetyStatus.UNKNOWN.value
    if not last_zone:
        return SafetyStatus.UNKNOWN.value
    # Open incidents in same zone → degrade status
    zone_incidents = list(
        db.scalars(
            select(orm.Incident).where(orm.Incident.zone_id == last_zone, orm.Incident.resolved.is_(False))
        )
    )
    if any(i.severity in (IncidentSeverity.CRITICAL.value, IncidentSeverity.HIGH.value) for i in zone_incidents):
        return SafetyStatus.CRITICAL.value
    if zone_incidents:
        return SafetyStatus.WARNING.value
    return SafetyStatus.SAFE.value


@router.get(
    "/students/{student_id}/profile",
    response_model=StudentProfile,
 )
def student_profile(
    student_id: str,
    db: Session = Depends(get_db),
    user: orm.User = Depends(require_teacher),
) -> StudentProfile:
    student = _find_student(db, student_id, school_scope(user))
    if student is None:
        raise HTTPException(status_code=404, detail=f"Student {student_id!r} not found")

    today = datetime.now(timezone.utc).date()

    # Index attendance by date for quick lookup
    student_records = db.scalars(
        select(orm.AttendanceRecord).where(
            orm.AttendanceRecord.student_id == student_id,
            orm.AttendanceRecord.date >= today - timedelta(days=365),
        )
    ).all()
    records_by_date: dict[date, orm.AttendanceRecord] = {r.date: r for r in student_records}

    # Today
    today_rec = records_by_date.get(today)
    today_status = today_rec.status if today_rec else AttendanceStatus.UNKNOWN.value
    arrival_iso = today_rec.arrival_time.isoformat() if today_rec and today_rec.arrival_time else None
    departure_iso = today_rec.departure_time.isoformat() if today_rec and today_rec.departure_time else None
    last_zone = today_rec.last_seen_zone if today_rec else None

    # Fallback to bracelet last-seen if no attendance record today
    bracelet = student.bracelet
    if last_zone is None and bracelet is not None:
        last_zone = bracelet.last_seen_zone

    # Weekly (last 7 days, oldest → newest)
    weekly: list[AttendanceDay] = []
    for offset in range(6, -1, -1):
        d = today - timedelta(days=offset)
        weekly.append(_to_attendance_day(db, records_by_date.get(d), d))

    # Last 30 days (newest → oldest)
    recent: list[AttendanceDay] = []
    present_count = 0
    total_count = 0
    for offset in range(0, 30):
        d = today - timedelta(days=offset)
        rec = records_by_date.get(d)
        recent.append(_to_attendance_day(db, rec, d))
        if rec is not None:
            total_count += 1
            if rec.status in _PRESENT_STATUSES:
                present_count += 1

    monthly_pct = round((present_count / total_count) * 100.0, 1) if total_count else 0.0
    streak = _compute_streak(records_by_date, today)

    # Notifications for parent/student
    ntfs_sorted = db.scalars(
        select(orm.Notification)
        .where(
            or_(
                orm.Notification.student_id == student_id,
                orm.Notification.parent_id == student.parent_id,
            )
        )
        .order_by(orm.Notification.sent_at.desc())
        .limit(20)
    ).all()
    unread = sum(1 for n in ntfs_sorted if not n.read)
    ntf_items = [
        NotificationItem(
            notification_id=n.notification_id,
            message=n.message,
            notification_type=n.notification_type,
            sent_at=n.sent_at.isoformat(),
            read=n.read,
        )
        for n in ntfs_sorted
    ]

    # Open incidents in last-seen zone
    open_incidents = (
        db.scalar(
            select(func.count()).select_from(orm.Incident).where(
                orm.Incident.zone_id == last_zone, orm.Incident.resolved.is_(False)
            )
        )
        if last_zone else 0
    )

    # Engagement summary from Unit 15
    eng_summary_obj = _get_agent().get_engagement_summary(student_id)
    eng_summary = (
        EngagementSummary(**eng_summary_obj.to_dict())
        if eng_summary_obj is not None
        else None
    )

    return StudentProfile(
        student_id=student.student_id,
        name=student.name,
        grade=student.grade,
        class_section=student.class_section,
        parent_id=student.parent_id,
        photo_initial=student.photo_initial,
        is_active=student.is_active,
        safety_status=_safety_status_for(db, student, last_zone),
        today_status=today_status,
        arrival_time=arrival_iso,
        departure_time=departure_iso,
        last_seen_zone=last_zone,
        last_seen_zone_label=_zone_label(db, last_zone),
        attendance_streak=streak,
        monthly_attendance_pct=monthly_pct,
        last_30_days_present=present_count,
        last_30_days_total=total_count,
        weekly_attendance=weekly,
        recent_attendance=recent,
        bracelet=_bracelet_summary(db, bracelet),
        notifications=ntf_items,
        unread_notifications=unread,
        open_incidents_in_last_zone=open_incidents,
        engagement_summary=eng_summary,
    )


# ── Behavioral History (Unit 15) ──────────────────────────────────────────────


@router.get(
    "/students/{student_id}/behavioral-history",
    response_model=list[EngagementSnapshotOut],
 )
def student_behavioral_history(
    student_id: str,
    days: int = 30,
    db: Session = Depends(get_db),
    user: orm.User = Depends(require_teacher),
) -> list[EngagementSnapshotOut]:
    """Return per-student engagement snapshots for the last N days (default 30),
    newest first.  Powered by Unit 15 — Pedagogical Behavioral Intelligence Agent.
    """
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")

    if _find_student(db, student_id, school_scope(user)) is None:
        raise HTTPException(status_code=404, detail=f"Student {student_id!r} not found")

    snapshots = _get_agent().get_behavioral_history(student_id, days=days)
    return [
        EngagementSnapshotOut(
            student_id=s.student_id,
            recorded_at=s.recorded_at.isoformat(),
            state=s.state.value,
            score=s.score,
            session_id=s.session_id,
            zone_id=s.zone_id,
            audio_context=s.audio_context,
            audio_visual_mismatch=s.audio_visual_mismatch,
        )
        for s in snapshots
    ]
