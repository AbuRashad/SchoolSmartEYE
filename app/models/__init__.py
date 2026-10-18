"""Domain models shared across SchoolSmartEYE units and services."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


# ── Enumerations ──────────────────────────────────────────────────────────────


class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    UNKNOWN = "unknown"


class SafetyStatus(str, Enum):
    SAFE = "safe"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ZoneType(str, Enum):
    CLASSROOM = "classroom"
    CORRIDOR = "corridor"
    ENTRANCE = "entrance"
    PLAYGROUND = "playground"
    CAFETERIA = "cafeteria"
    ADMINISTRATIVE = "administrative"
    RESTROOM = "restroom"
    PARKING = "parking"


class ReportType(str, Enum):
    OPERATIONAL = "operational"
    ANALYTICAL = "analytical"
    SUPERVISORY = "supervisory"
    MINISTERIAL = "ministerial"


class EngagementState(str, Enum):
    ATTENTIVE = "attentive"
    ENGAGED = "engaged"
    DISTRACTED = "distracted"
    DROWSY = "drowsy"
    UNKNOWN = "unknown"


# ── Core Domain Models ────────────────────────────────────────────────────────


@dataclass
class Student:
    """A student enrolled in the school."""
    student_id: str
    name: str
    grade: str
    class_section: str
    parent_id: str
    photo_initial: str = ""
    is_active: bool = True


@dataclass
class Teacher:
    """A teacher or staff member at the school."""
    teacher_id: str
    name: str
    subject: str
    assigned_classes: list[str] = field(default_factory=list)
    is_active: bool = True


@dataclass
class SchoolZone:
    """A physical zone or area within the school campus."""
    zone_id: str
    label: str
    zone_type: ZoneType
    capacity: int = 0
    floor: int = 1
    coordinates: tuple[int, int] = (0, 0)


@dataclass
class DailyAttendance:
    """Aggregated daily attendance record for a student."""
    student_id: str
    date: date
    status: AttendanceStatus
    arrival_time: Optional[datetime] = None
    departure_time: Optional[datetime] = None
    last_seen_zone: Optional[str] = None


@dataclass
class SafetyIncident:
    """A safety or behavioral incident detected on campus."""
    incident_id: str
    zone_id: str
    severity: IncidentSeverity
    description: str
    detected_at: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


@dataclass
class CameraFeed:
    """Metadata for an active surveillance camera."""
    camera_id: str
    zone_id: str
    label: str
    resolution: tuple[int, int] = (1280, 720)
    fps: int = 25
    is_active: bool = True


@dataclass
class SchoolMetrics:
    """Snapshot of key school performance metrics."""
    computed_at: datetime
    total_students: int
    present_today: int
    attendance_rate: float
    active_cameras: int
    open_incidents: int
    ssi_score: float
    benchmark: float = 75.0

    @property
    def above_benchmark(self) -> bool:
        return self.ssi_score >= self.benchmark


@dataclass
class ReportRecord:
    """A generated report artifact."""
    report_id: str
    title: str
    report_type: ReportType
    period_label: str
    generated_at: datetime
    is_ready: bool = True
    content_summary: str = ""


@dataclass
class NotificationMessage:
    """A push notification sent to a parent."""
    notification_id: str
    parent_id: str
    student_id: str
    message: str
    notification_type: str
    sent_at: datetime
    read: bool = False


@dataclass
class VisitorRecord:
    """A visitor log entry."""
    visitor_id: str
    name: str
    purpose: str
    host_id: str
    check_in: datetime
    check_out: Optional[datetime] = None
    badge_number: str = ""


@dataclass
class TransportRoute:
    """A school bus route definition."""
    route_id: str
    bus_number: str
    driver_name: str
    stops: list[str] = field(default_factory=list)
    is_active: bool = True
    current_location: Optional[str] = None


@dataclass
class Bracelet:
    """A wearable tracker bracelet assigned to a student.

    Used by the attendance / safety subsystem (Units 02, 07, 12) to correlate
    physical presence with camera-based detection. Designed to be hardware-
    agnostic — any BLE / LoRa / GPS tag can hydrate this record.
    """
    bracelet_id: str
    student_id: str
    mac_address: str
    battery_level: int = 100  # 0-100 percent
    is_active: bool = True
    last_seen_zone: Optional[str] = None
    last_seen_at: Optional[datetime] = None
    firmware_version: str = "1.0.0"
    notes: str = ""


@dataclass
class EngagementSnapshot:
    """A single per-student behavioral engagement reading captured by Unit 15.

    Produced by pose estimation / audio analysis for each student during a
    class session. Multiple snapshots per session build the behavioral timeline.
    """
    student_id: str
    recorded_at: datetime
    state: EngagementState
    score: float          # 0.0 (fully disengaged) → 1.0 (fully engaged)
    session_id: str
    zone_id: Optional[str] = None
    audio_context: Optional[str] = None      # e.g. "speaking", "silent", "disturbance"
    audio_visual_mismatch: bool = False      # visual state contradicts audio context


@dataclass
class AgentFeedback:
    """A teacher annotation confirming or correcting a Unit 15 prediction."""
    feedback_id: str
    session_id: str
    student_id: str
    predicted_state: EngagementState
    confirmed_state: EngagementState
    teacher_notes: str
    recorded_at: datetime
