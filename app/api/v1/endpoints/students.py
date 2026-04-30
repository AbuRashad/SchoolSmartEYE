"""Students & zones CRUD used by the Control Panel.

All storage is the in-memory list in `app.services.seed_data`. Mutations are
guarded by a module-level lock because FastAPI may serve concurrent requests
from multiple threads.
"""
from __future__ import annotations

import threading
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.models import (
    AttendanceStatus,
    Bracelet,
    DailyAttendance,
    IncidentSeverity,
    SafetyStatus,
    Student,
)
from app.services import seed_data
from app.services.pedagogical_agent import PedagogicalAgentService

router = APIRouter(tags=["control"])

_lock = threading.Lock()

# Lazy singleton for the pedagogical agent service (backed by seed_data stores)
_agent: PedagogicalAgentService | None = None


def _get_agent() -> PedagogicalAgentService:
    global _agent  # noqa: PLW0603
    if _agent is None:
        from app.core.config import settings
        _agent = PedagogicalAgentService(
            snapshots=seed_data.engagement_snapshots,
            feedback_log=seed_data.agent_feedback_log,
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


def _serialize(s: Student) -> StudentOut:
    return StudentOut(
        student_id=s.student_id,
        name=s.name,
        grade=s.grade,
        class_section=s.class_section,
        parent_id=s.parent_id,
        photo_initial=s.photo_initial,
        is_active=s.is_active,
    )


def _find_student(student_id: str) -> Student | None:
    return next((s for s in seed_data.students if s.student_id == student_id), None)


# ── Students ──────────────────────────────────────────────────────────────────


@router.get("/students", response_model=list[StudentOut])
def list_students() -> list[StudentOut]:
    with _lock:
        return [_serialize(s) for s in seed_data.students]


@router.post("/students", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreate) -> StudentOut:
    with _lock:
        if _find_student(payload.student_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Student {payload.student_id!r} already exists",
            )
        initial = payload.photo_initial or (payload.name[:1].upper() if payload.name else "?")
        student = Student(
            student_id=payload.student_id,
            name=payload.name,
            grade=payload.grade,
            class_section=payload.class_section,
            parent_id=payload.parent_id,
            photo_initial=initial,
            is_active=payload.is_active,
        )
        seed_data.students.append(student)
        return _serialize(student)


@router.patch("/students/{student_id}", response_model=StudentOut)
def update_student(student_id: str, payload: StudentUpdate) -> StudentOut:
    with _lock:
        student = _find_student(student_id)
        if student is None:
            raise HTTPException(status_code=404, detail=f"Student {student_id!r} not found")
        if payload.name is not None:
            student.name = payload.name
        if payload.grade is not None:
            student.grade = payload.grade
        if payload.class_section is not None:
            student.class_section = payload.class_section
        if payload.parent_id is not None:
            student.parent_id = payload.parent_id
        if payload.photo_initial is not None:
            student.photo_initial = payload.photo_initial
        if payload.is_active is not None:
            student.is_active = payload.is_active
        return _serialize(student)


@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: str) -> Response:
    with _lock:
        student = _find_student(student_id)
        if student is None:
            raise HTTPException(status_code=404, detail=f"Student {student_id!r} not found")
        seed_data.students.remove(student)
        # Cascade: detach bracelets referencing this student
        for br in list(seed_data.bracelets):
            if br.student_id == student_id:
                seed_data.bracelets.remove(br)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── Zones (read-only) ─────────────────────────────────────────────────────────


@router.get("/zones", response_model=list[ZoneOut])
def list_zones() -> list[ZoneOut]:
    return [
        ZoneOut(
            zone_id=z.zone_id,
            label=z.label,
            zone_type=z.zone_type.value,
            capacity=z.capacity,
            floor=z.floor,
        )
        for z in seed_data.zones
    ]


# ── Aggregated Student Profile ────────────────────────────────────────────────


def _zone_label(zone_id: str | None) -> str | None:
    if not zone_id:
        return None
    zone = next((z for z in seed_data.zones if z.zone_id == zone_id), None)
    return zone.label if zone else zone_id


def _find_bracelet(student_id: str) -> Bracelet | None:
    return next((b for b in seed_data.bracelets if b.student_id == student_id), None)


def _bracelet_summary(bracelet: Bracelet | None) -> BraceletSummary | None:
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
        last_seen_zone_label=_zone_label(bracelet.last_seen_zone),
        last_seen_at=bracelet.last_seen_at.isoformat() if bracelet.last_seen_at else None,
        firmware_version=bracelet.firmware_version,
        notes=bracelet.notes,
        low_battery=bracelet.battery_level <= threshold,
    )


def _to_attendance_day(rec: DailyAttendance | None, day: date) -> AttendanceDay:
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
        status=rec.status.value,
        arrival_time=rec.arrival_time.isoformat() if rec.arrival_time else None,
        departure_time=rec.departure_time.isoformat() if rec.departure_time else None,
        last_seen_zone=rec.last_seen_zone,
        last_seen_zone_label=_zone_label(rec.last_seen_zone),
    )


def _compute_streak(records_by_date: dict[date, DailyAttendance], today: date) -> int:
    streak = 0
    cursor = today
    for _ in range(365):  # safety cap
        rec = records_by_date.get(cursor)
        if rec and rec.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE):
            streak += 1
            cursor = cursor - timedelta(days=1)
        else:
            break
    return streak


def _safety_status_for(student: Student, last_zone: str | None) -> str:
    if not student.is_active:
        return SafetyStatus.UNKNOWN.value
    if not last_zone:
        return SafetyStatus.UNKNOWN.value
    # Open incidents in same zone → degrade status
    zone_incidents = [
        i for i in seed_data.incidents
        if i.zone_id == last_zone and not i.resolved
    ]
    if any(i.severity in (IncidentSeverity.CRITICAL, IncidentSeverity.HIGH) for i in zone_incidents):
        return SafetyStatus.CRITICAL.value
    if zone_incidents:
        return SafetyStatus.WARNING.value
    return SafetyStatus.SAFE.value


@router.get("/students/{student_id}/profile", response_model=StudentProfile)
def student_profile(student_id: str) -> StudentProfile:
    with _lock:
        student = _find_student(student_id)
        if student is None:
            raise HTTPException(status_code=404, detail=f"Student {student_id!r} not found")

        today = datetime.now(timezone.utc).date()

        # Index attendance by date for quick lookup
        student_records = [r for r in seed_data.attendance_records if r.student_id == student_id]
        records_by_date: dict[date, DailyAttendance] = {r.date: r for r in student_records}

        # Today
        today_rec = records_by_date.get(today)
        today_status = today_rec.status.value if today_rec else AttendanceStatus.UNKNOWN.value
        arrival_iso = today_rec.arrival_time.isoformat() if today_rec and today_rec.arrival_time else None
        departure_iso = today_rec.departure_time.isoformat() if today_rec and today_rec.departure_time else None
        last_zone = today_rec.last_seen_zone if today_rec else None

        # Fallback to bracelet last-seen if no attendance record today
        bracelet = _find_bracelet(student_id)
        if last_zone is None and bracelet is not None:
            last_zone = bracelet.last_seen_zone

        # Weekly (last 7 days, oldest → newest)
        weekly: list[AttendanceDay] = []
        for offset in range(6, -1, -1):
            d = today - timedelta(days=offset)
            weekly.append(_to_attendance_day(records_by_date.get(d), d))

        # Last 30 days (newest → oldest)
        recent: list[AttendanceDay] = []
        present_count = 0
        total_count = 0
        for offset in range(0, 30):
            d = today - timedelta(days=offset)
            rec = records_by_date.get(d)
            recent.append(_to_attendance_day(rec, d))
            if rec is not None:
                total_count += 1
                if rec.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE):
                    present_count += 1

        monthly_pct = round((present_count / total_count) * 100.0, 1) if total_count else 0.0
        streak = _compute_streak(records_by_date, today)

        # Notifications for parent/student
        ntfs = [
            n for n in seed_data.notifications
            if n.student_id == student_id or n.parent_id == student.parent_id
        ]
        ntfs_sorted = sorted(ntfs, key=lambda n: n.sent_at, reverse=True)[:20]
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
            sum(1 for i in seed_data.incidents if i.zone_id == last_zone and not i.resolved)
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
            safety_status=_safety_status_for(student, last_zone),
            today_status=today_status,
            arrival_time=arrival_iso,
            departure_time=departure_iso,
            last_seen_zone=last_zone,
            last_seen_zone_label=_zone_label(last_zone),
            attendance_streak=streak,
            monthly_attendance_pct=monthly_pct,
            last_30_days_present=present_count,
            last_30_days_total=total_count,
            weekly_attendance=weekly,
            recent_attendance=recent,
            bracelet=_bracelet_summary(bracelet),
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
) -> list[EngagementSnapshotOut]:
    """Return per-student engagement snapshots for the last N days (default 30),
    newest first.  Powered by Unit 15 — Pedagogical Behavioral Intelligence Agent.
    """
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 1 and 365")

    with _lock:
        student = _find_student(student_id)
        if student is None:
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
