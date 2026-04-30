"""Demo seed data for SchoolSmartEYE — realistic Arab school monitoring context.

Populated on startup so the system has meaningful data to display immediately.
All storage is in-memory; no database dependency required.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.models import (
    AgentFeedback,
    AttendanceStatus,
    Bracelet,
    CameraFeed,
    DailyAttendance,
    EngagementSnapshot,
    EngagementState,
    IncidentSeverity,
    NotificationMessage,
    ReportRecord,
    ReportType,
    SafetyIncident,
    SafetyStatus,
    SchoolMetrics,
    SchoolZone,
    Student,
    Teacher,
    TransportRoute,
    VisitorRecord,
    ZoneType,
)


# ── In-memory stores ──────────────────────────────────────────────────────────

students: list[Student] = []
teachers: list[Teacher] = []
zones: list[SchoolZone] = []
cameras: list[CameraFeed] = []
attendance_records: list[DailyAttendance] = []
incidents: list[SafetyIncident] = []
reports: list[ReportRecord] = []
notifications: list[NotificationMessage] = []
visitors: list[VisitorRecord] = []
transport_routes: list[TransportRoute] = []
bracelets: list[Bracelet] = []
engagement_snapshots: list[EngagementSnapshot] = []
agent_feedback_log: list[AgentFeedback] = []


def _utc(hour: int = 8, minute: int = 0, day_offset: int = 0) -> datetime:
    base = datetime.now(timezone.utc).replace(hour=hour, minute=minute, second=0, microsecond=0)
    return base + timedelta(days=day_offset)


def _today() -> date:
    return datetime.now(timezone.utc).date()


# ── Zones ─────────────────────────────────────────────────────────────────────


def _seed_zones() -> None:
    zones.extend(
        [
            SchoolZone("zone-main-gate", "Main Gate", ZoneType.ENTRANCE, capacity=50, floor=0, coordinates=(0, 0)),
            SchoolZone("zone-corridor-a", "Corridor A", ZoneType.CORRIDOR, capacity=80, floor=1, coordinates=(1, 0)),
            SchoolZone("zone-corridor-b", "Corridor B", ZoneType.CORRIDOR, capacity=80, floor=2, coordinates=(1, 1)),
            SchoolZone("zone-classroom-1a", "Classroom 1A", ZoneType.CLASSROOM, capacity=35, floor=1, coordinates=(2, 0)),
            SchoolZone("zone-classroom-1b", "Classroom 1B", ZoneType.CLASSROOM, capacity=35, floor=1, coordinates=(2, 1)),
            SchoolZone("zone-classroom-2a", "Classroom 2A", ZoneType.CLASSROOM, capacity=35, floor=2, coordinates=(3, 0)),
            SchoolZone("zone-classroom-2b", "Classroom 2B", ZoneType.CLASSROOM, capacity=35, floor=2, coordinates=(3, 1)),
            SchoolZone("zone-cafeteria", "Cafeteria", ZoneType.CAFETERIA, capacity=200, floor=0, coordinates=(0, 1)),
            SchoolZone("zone-playground", "Playground", ZoneType.PLAYGROUND, capacity=300, floor=0, coordinates=(0, 2)),
            SchoolZone("zone-admin", "Administrative Office", ZoneType.ADMINISTRATIVE, capacity=20, floor=1, coordinates=(4, 0)),
            SchoolZone("zone-library", "Library / Learning Commons", ZoneType.CLASSROOM, capacity=60, floor=1, coordinates=(4, 1)),
            SchoolZone("zone-parking", "Bus Parking Zone", ZoneType.PARKING, capacity=100, floor=0, coordinates=(0, 3)),
        ]
    )


# ── Cameras ───────────────────────────────────────────────────────────────────


def _seed_cameras() -> None:
    camera_specs = [
        ("cam-01", "zone-main-gate", "Main Gate — Entry"),
        ("cam-02", "zone-main-gate", "Main Gate — Exit"),
        ("cam-03", "zone-corridor-a", "Corridor A — Floor 1"),
        ("cam-04", "zone-corridor-b", "Corridor B — Floor 2"),
        ("cam-05", "zone-classroom-1a", "Classroom 1A"),
        ("cam-06", "zone-classroom-1b", "Classroom 1B"),
        ("cam-07", "zone-classroom-2a", "Classroom 2A"),
        ("cam-08", "zone-classroom-2b", "Classroom 2B"),
        ("cam-09", "zone-cafeteria", "Cafeteria North"),
        ("cam-10", "zone-cafeteria", "Cafeteria South"),
        ("cam-11", "zone-playground", "Playground"),
        ("cam-12", "zone-library", "Library / Learning Commons"),
    ]
    cameras.extend(
        CameraFeed(cid, zid, label, resolution=(1280, 720), fps=25, is_active=True)
        for cid, zid, label in camera_specs
    )


# ── Teachers ──────────────────────────────────────────────────────────────────


def _seed_teachers() -> None:
    teachers.extend(
        [
            Teacher("T001", "Mohammed Al-Harbi", "Mathematics", ["1A", "2A"]),
            Teacher("T002", "Fatima Al-Zahrani", "Arabic Language", ["1A", "1B"]),
            Teacher("T003", "Ahmed Al-Qahtani", "Science", ["2A", "2B"]),
            Teacher("T004", "Noura Al-Shammari", "English", ["1B", "2B"]),
            Teacher("T005", "Khalid Al-Dossari", "Islamic Studies", ["1A", "1B", "2A", "2B"]),
            Teacher("T006", "Sara Al-Otaibi", "Physical Education", ["1A", "2A"]),
        ]
    )


# ── Students ──────────────────────────────────────────────────────────────────


_STUDENT_DATA = [
    ("STU-2024-0847", "Ahmed Al-Rashidi", "Grade 9 — Class A", "1A", "P001", "A"),
    ("STU-2024-0848", "Omar Al-Faisal", "Grade 9 — Class A", "1A", "P002", "O"),
    ("STU-2024-0849", "Sara Al-Mutairi", "Grade 9 — Class A", "1A", "P003", "S"),
    ("STU-2024-0850", "Nora Al-Ghamdi", "Grade 9 — Class B", "1B", "P004", "N"),
    ("STU-2024-0851", "Khaled Al-Shamrani", "Grade 9 — Class B", "1B", "P005", "K"),
    ("STU-2024-0852", "Layla Al-Anazi", "Grade 10 — Class A", "2A", "P006", "L"),
    ("STU-2024-0853", "Youssef Al-Harbi", "Grade 10 — Class A", "2A", "P007", "Y"),
    ("STU-2024-0854", "Hessa Al-Zahrani", "Grade 10 — Class B", "2B", "P008", "H"),
    ("STU-2024-0855", "Faisal Al-Dosari", "Grade 10 — Class B", "2B", "P009", "F"),
    ("STU-2024-0856", "Reem Al-Qahtani", "Grade 9 — Class A", "1A", "P010", "R"),
]


def _seed_students() -> None:
    students.extend(
        Student(sid, name, grade, cls, pid, initial)
        for sid, name, grade, cls, pid, initial in _STUDENT_DATA
    )


# ── Attendance ─────────────────────────────────────────────────────────────────


def _seed_attendance() -> None:
    today = _today()
    # Mark all students present today (with realistic arrival times)
    arrival_times = [
        ("07:42", "zone-classroom-1a"),
        ("07:38", "zone-classroom-1a"),
        ("07:55", "zone-corridor-a"),
        ("07:45", "zone-classroom-1b"),
        ("07:50", "zone-classroom-1b"),
        ("07:41", "zone-classroom-2a"),
        ("07:39", "zone-classroom-2a"),
        ("07:58", "zone-classroom-2b"),
        ("07:47", "zone-classroom-2b"),
        ("07:52", "zone-corridor-a"),
    ]
    for i, (sid, _, _, _, _, _) in enumerate(_STUDENT_DATA):
        hm = arrival_times[i][0].split(":")
        arrival = datetime.now(timezone.utc).replace(
            hour=int(hm[0]), minute=int(hm[1]), second=0, microsecond=0
        )
        status = AttendanceStatus.PRESENT if i != 3 else AttendanceStatus.LATE
        attendance_records.append(
            DailyAttendance(
                student_id=sid,
                date=today,
                status=status,
                arrival_time=arrival,
                last_seen_zone=arrival_times[i][1],
            )
        )

    # Add last-week records
    for day_offset in range(-7, 0):
        past_date = today + timedelta(days=day_offset)
        for j, (sid, _, _, _, _, _) in enumerate(_STUDENT_DATA):
            status = AttendanceStatus.ABSENT if (j + abs(day_offset)) % 7 == 0 else AttendanceStatus.PRESENT
            attendance_records.append(
                DailyAttendance(student_id=sid, date=past_date, status=status)
            )


# ── Incidents ─────────────────────────────────────────────────────────────────


def _seed_incidents() -> None:
    now = datetime.now(timezone.utc)
    incident_data = [
        ("INC-001", "zone-corridor-a", IncidentSeverity.HIGH, "Behavioral anomaly: sudden crowd surge detected near stairwell", -2),
        ("INC-002", "zone-playground", IncidentSeverity.MEDIUM, "Elevated motion entropy during break time — possible altercation", -1),
        ("INC-003", "zone-cafeteria", IncidentSeverity.LOW, "Crowd density at 78% capacity during lunch rush", 0),
        ("INC-004", "zone-main-gate", IncidentSeverity.MEDIUM, "Unregistered visitor attempted entry without badge", -3),
        ("INC-005", "zone-classroom-2b", IncidentSeverity.LOW, "Loitering detected in corridor outside Classroom 2B", -1),
    ]
    for inc_id, zone_id, severity, desc, day_offset in incident_data:
        detected_at = now + timedelta(hours=day_offset * 8)
        resolved = day_offset < 0
        incidents.append(
            SafetyIncident(
                incident_id=inc_id,
                zone_id=zone_id,
                severity=severity,
                description=desc,
                detected_at=detected_at,
                resolved=resolved,
                resolved_at=detected_at + timedelta(hours=1) if resolved else None,
            )
        )


# ── Reports ───────────────────────────────────────────────────────────────────


def _seed_reports() -> None:
    now = datetime.now(timezone.utc)
    report_data = [
        ("RPT-001", "Daily Operational Summary", ReportType.OPERATIONAL, "Today", 0),
        ("RPT-002", "Weekly Incident Analysis", ReportType.ANALYTICAL, "This Week", -1),
        ("RPT-003", "Monthly Safety Assessment", ReportType.SUPERVISORY, "March 2026", -3),
        ("RPT-004", "Q1 2026 Ministerial Report", ReportType.MINISTERIAL, "Q1 2026", -7),
    ]
    for rpt_id, title, rpt_type, period, day_offset in report_data:
        reports.append(
            ReportRecord(
                report_id=rpt_id,
                title=title,
                report_type=rpt_type,
                period_label=period,
                generated_at=now + timedelta(days=day_offset),
                is_ready=True,
                content_summary=f"Auto-generated {rpt_type.value} report for {period}.",
            )
        )


# ── Notifications ─────────────────────────────────────────────────────────────


def _seed_notifications() -> None:
    now = datetime.now(timezone.utc)
    notification_data = [
        ("NTF-001", "P001", "STU-2024-0847", "Ahmed arrived at school at 07:42 AM", "attendance", -8),
        ("NTF-002", "P001", "STU-2024-0847", "Ahmed is in Learning Commons — all clear", "safety", -5),
        ("NTF-003", "P001", "STU-2024-0847", "School Safety Index is above benchmark today", "info", -3),
        ("NTF-004", "P001", "STU-2024-0847", "Lunch break started. Ahmed in cafeteria zone.", "attendance", -1),
    ]
    for ntf_id, parent_id, student_id, message, ntf_type, hour_offset in notification_data:
        notifications.append(
            NotificationMessage(
                notification_id=ntf_id,
                parent_id=parent_id,
                student_id=student_id,
                message=message,
                notification_type=ntf_type,
                sent_at=now + timedelta(hours=hour_offset),
                read=hour_offset < -2,
            )
        )


# ── Visitors ──────────────────────────────────────────────────────────────────


def _seed_visitors() -> None:
    now = datetime.now(timezone.utc)
    visitor_data = [
        ("VIS-001", "Dr. Hassan Al-Sayed", "School Inspection", "T005", -2, True, "BADGE-101"),
        ("VIS-002", "Eng. Lina Al-Sharif", "IT Infrastructure Review", "T001", -1, True, "BADGE-102"),
        ("VIS-003", "Mrs. Rania Al-Hajri", "Parent Meeting", "T002", 0, False, "BADGE-103"),
    ]
    for vis_id, name, purpose, host, hour_offset, checked_out, badge in visitor_data:
        check_in = now + timedelta(hours=hour_offset)
        visitors.append(
            VisitorRecord(
                visitor_id=vis_id,
                name=name,
                purpose=purpose,
                host_id=host,
                check_in=check_in,
                check_out=check_in + timedelta(hours=2) if checked_out else None,
                badge_number=badge,
            )
        )


# ── Transport Routes ──────────────────────────────────────────────────────────


def _seed_bracelets() -> None:
    now = datetime.now(timezone.utc)
    bracelet_data = [
        ("BR-0001", "STU-2024-0847", "AA:BB:CC:00:00:01", 92, "zone-classroom-1a"),
        ("BR-0002", "STU-2024-0848", "AA:BB:CC:00:00:02", 78, "zone-classroom-1a"),
        ("BR-0003", "STU-2024-0849", "AA:BB:CC:00:00:03", 64, "zone-corridor-a"),
        ("BR-0004", "STU-2024-0850", "AA:BB:CC:00:00:04", 41, "zone-classroom-1b"),
        ("BR-0005", "STU-2024-0852", "AA:BB:CC:00:00:05", 88, "zone-classroom-2a"),
    ]
    for bid, sid, mac, battery, zone in bracelet_data:
        bracelets.append(
            Bracelet(
                bracelet_id=bid,
                student_id=sid,
                mac_address=mac,
                battery_level=battery,
                last_seen_zone=zone,
                last_seen_at=now,
                firmware_version="1.2.0",
            )
        )


def _seed_transport() -> None:
    transport_routes.extend(
        [
            TransportRoute(
                route_id="RT-001",
                bus_number="BUS-01",
                driver_name="Saleh Al-Matroudi",
                stops=["Olaya District", "Al-Malaz", "Al-Rawdah", "School"],
                is_active=True,
                current_location="Al-Rawdah",
            ),
            TransportRoute(
                route_id="RT-002",
                bus_number="BUS-02",
                driver_name="Ibrahim Al-Qurashi",
                stops=["Al-Murabba", "Al-Sulaymaniyah", "Al-Wurud", "School"],
                is_active=True,
                current_location="School",
            ),
            TransportRoute(
                route_id="RT-003",
                bus_number="BUS-03",
                driver_name="Majid Al-Shehri",
                stops=["Al-Naseem", "Al-Hazm", "Al-Batha", "School"],
                is_active=False,
                current_location=None,
            ),
        ]
    )


# ── Engagement Snapshots (Unit 15) ────────────────────────────────────────────

# Pre-defined engagement trajectories per student across recent sessions.
# Each tuple: (state, score, audio_context, audio_visual_mismatch)
_STUDENT_SESSION_PROFILES: dict[str, list[tuple[EngagementState, float, str | None, bool]]] = {
    "STU-2024-0847": [  # Ahmed — consistently engaged
        (EngagementState.ENGAGED, 0.92, "speaking", False),
        (EngagementState.ATTENTIVE, 0.78, "silent", False),
        (EngagementState.ENGAGED, 0.88, "speaking", False),
    ],
    "STU-2024-0848": [  # Omar — attentive but occasionally distracted
        (EngagementState.ATTENTIVE, 0.74, "silent", False),
        (EngagementState.DISTRACTED, 0.28, "silent", False),
        (EngagementState.ATTENTIVE, 0.71, "silent", False),
    ],
    "STU-2024-0849": [  # Sara — high engagement with audio-visual mismatch
        (EngagementState.ENGAGED, 0.90, "speaking", False),
        (EngagementState.DISTRACTED, 0.25, "speaking", True),  # speaking but distracted posture
        (EngagementState.ENGAGED, 0.85, "speaking", False),
    ],
    "STU-2024-0850": [  # Nora — drowsy trend
        (EngagementState.DROWSY, 0.18, "silent", False),
        (EngagementState.DISTRACTED, 0.32, "silent", False),
        (EngagementState.DROWSY, 0.14, "silent", False),
    ],
    "STU-2024-0851": [  # Khaled — improving
        (EngagementState.DISTRACTED, 0.30, "silent", False),
        (EngagementState.ATTENTIVE, 0.65, "silent", False),
        (EngagementState.ENGAGED, 0.80, "speaking", False),
    ],
    "STU-2024-0852": [  # Layla — stable attentive
        (EngagementState.ATTENTIVE, 0.72, "silent", False),
        (EngagementState.ATTENTIVE, 0.75, "silent", False),
        (EngagementState.ATTENTIVE, 0.70, "silent", False),
    ],
    "STU-2024-0853": [  # Youssef — very engaged
        (EngagementState.ENGAGED, 0.95, "speaking", False),
        (EngagementState.ENGAGED, 0.91, "speaking", False),
        (EngagementState.ENGAGED, 0.93, "speaking", False),
    ],
    "STU-2024-0854": [  # Hessa — audio-visual mismatch pattern
        (EngagementState.ATTENTIVE, 0.68, "silent", False),
        (EngagementState.DISTRACTED, 0.29, "speaking", True),  # speaking but distracted
        (EngagementState.ATTENTIVE, 0.65, "silent", False),
    ],
    "STU-2024-0855": [  # Faisal — disengaged
        (EngagementState.DISTRACTED, 0.22, "silent", False),
        (EngagementState.DROWSY, 0.12, "silent", False),
        (EngagementState.DISTRACTED, 0.25, "silent", False),
    ],
    "STU-2024-0856": [  # Reem — engaged with context
        (EngagementState.ENGAGED, 0.87, "speaking", False),
        (EngagementState.ATTENTIVE, 0.76, "silent", False),
        (EngagementState.ENGAGED, 0.82, "speaking", False),
    ],
}

_SESSION_ZONES = [
    "zone-classroom-1a",
    "zone-classroom-1b",
    "zone-classroom-2a",
    "zone-classroom-2b",
]


def _seed_engagement_snapshots() -> None:
    """Seed three sessions of engagement data across the last 3 days."""
    now = datetime.now(timezone.utc)
    session_specs = [
        ("SES-TODAY-AM", 0, 8, 30),    # today 08:30
        ("SES-YEST-AM", -1, 8, 30),    # yesterday 08:30
        ("SES-2D-AM", -2, 9, 0),       # 2 days ago 09:00
    ]

    zone_list = _SESSION_ZONES
    for session_id, day_offset, hour, minute in session_specs:
        base_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=day_offset)
        for idx, (sid, _, _, _, _, _) in enumerate(_STUDENT_DATA):
            profile = _STUDENT_SESSION_PROFILES.get(sid, [])
            # Pick the snapshot profile entry matching the session index (cycle through)
            entry = profile[session_specs.index((session_id, day_offset, hour, minute)) % len(profile)]
            state, score, audio_context, mismatch = entry
            zone_id = zone_list[idx % len(zone_list)]
            # Stagger snapshot times within session (one every 10 minutes)
            snap_time = base_time + timedelta(minutes=10 * idx)
            engagement_snapshots.append(
                EngagementSnapshot(
                    student_id=sid,
                    recorded_at=snap_time,
                    state=state,
                    score=score,
                    session_id=session_id,
                    zone_id=zone_id,
                    audio_context=audio_context,
                    audio_visual_mismatch=mismatch,
                )
            )

    # Add a few additional historical snapshots for trend analysis (7 days back)
    for day_offset in range(-7, -2):
        session_id = f"SES-HIST-{abs(day_offset)}"
        base_time = now.replace(hour=8, minute=30, second=0, microsecond=0) + timedelta(days=day_offset)
        for idx, (sid, _, _, _, _, _) in enumerate(_STUDENT_DATA):
            profile = _STUDENT_SESSION_PROFILES.get(sid, [])
            entry = profile[idx % len(profile)]
            state, score, audio_context, mismatch = entry
            engagement_snapshots.append(
                EngagementSnapshot(
                    student_id=sid,
                    recorded_at=base_time + timedelta(minutes=5 * idx),
                    state=state,
                    score=score,
                    session_id=session_id,
                    zone_id=zone_list[idx % len(zone_list)],
                    audio_context=audio_context,
                    audio_visual_mismatch=mismatch,
                )
            )


def _seed_agent_feedback() -> None:
    """Seed a few teacher feedback entries to demonstrate the self-evaluation loop."""
    now = datetime.now(timezone.utc)
    feedback_entries = [
        (
            "FB-001", "SES-YEST-AM", "STU-2024-0850",
            EngagementState.DROWSY, EngagementState.DROWSY,
            "Confirmed — student appeared tired throughout morning session.",
            -26,
        ),
        (
            "FB-002", "SES-YEST-AM", "STU-2024-0849",
            EngagementState.DISTRACTED, EngagementState.ENGAGED,
            "Incorrect — student was actively asking questions.",
            -25,
        ),
        (
            "FB-003", "SES-2D-AM", "STU-2024-0847",
            EngagementState.ENGAGED, EngagementState.ENGAGED,
            "Accurate prediction.",
            -50,
        ),
    ]
    for fb_id, session_id, student_id, pred, confirmed, notes, hour_offset in feedback_entries:
        agent_feedback_log.append(
            AgentFeedback(
                feedback_id=fb_id,
                session_id=session_id,
                student_id=student_id,
                predicted_state=pred,
                confirmed_state=confirmed,
                teacher_notes=notes,
                recorded_at=now + timedelta(hours=hour_offset),
            )
        )


# ── Entry-point ───────────────────────────────────────────────────────────────


def populate() -> None:
    """Populate all in-memory stores with demo data.

    Idempotent — calling multiple times will not duplicate data.
    """
    if students:  # already seeded
        return
    _seed_zones()
    _seed_cameras()
    _seed_teachers()
    _seed_students()
    _seed_attendance()
    _seed_incidents()
    _seed_reports()
    _seed_notifications()
    _seed_visitors()
    _seed_transport()
    _seed_bracelets()
    _seed_engagement_snapshots()
    _seed_agent_feedback()


def get_school_metrics() -> SchoolMetrics:
    """Return a live snapshot of aggregated school metrics."""
    present = sum(1 for r in attendance_records if r.date == _today() and r.status == AttendanceStatus.PRESENT)
    total = len([s for s in students if s.is_active])
    open_incidents = sum(1 for i in incidents if not i.resolved)
    active_cameras = sum(1 for c in cameras if c.is_active)
    return SchoolMetrics(
        computed_at=datetime.now(timezone.utc),
        total_students=total,
        present_today=present,
        attendance_rate=round(present / max(total, 1) * 100, 1),
        active_cameras=active_cameras,
        open_incidents=open_incidents,
        ssi_score=81.4,
        benchmark=75.0,
    )
