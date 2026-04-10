from datetime import datetime, timedelta

from app.services.attendance_safety_integration import (
    AttendanceRecord,
    evaluate_attendance_safety,
    StudentDetection,
)


def test_present_student_detected_in_expected_zone_has_no_alert() -> None:
    now = datetime(2026, 4, 6, 8, 30)
    attendance = [
        AttendanceRecord(
            student_id="S-100",
            status="Present",
            expected_zone="Classroom-A",
            expected_path=("Corridor-A",),
            recorded_at=now - timedelta(minutes=5),
        )
    ]
    detections = [
        StudentDetection(
            student_id="S-100",
            zone="Classroom-A",
            detected_at=now,
        )
    ]

    alerts = evaluate_attendance_safety(attendance, detections, now=now)

    assert alerts == []


def test_present_student_detected_in_restricted_zone_triggers_alert() -> None:
    now = datetime(2026, 4, 6, 9, 0)
    attendance = [
        AttendanceRecord(
            student_id="S-101",
            status="Present",
            expected_zone="Playground",
            expected_path=("Main-Corridor",),
            recorded_at=now - timedelta(minutes=2),
        )
    ]
    detections = [
        StudentDetection(
            student_id="S-101",
            zone="Restricted-Lab",
            detected_at=now,
        )
    ]

    alerts = evaluate_attendance_safety(
        attendance,
        detections,
        restricted_zones={"Restricted-Lab"},
        now=now,
    )

    assert len(alerts) == 1
    assert alerts[0].severity == "high"
    assert alerts[0].reason == "restricted_zone_detected"
    assert alerts[0].detected_zone == "Restricted-Lab"


def test_present_student_missing_from_all_camera_feeds_triggers_critical_alert() -> None:
    now = datetime(2026, 4, 6, 10, 15)
    attendance = [
        AttendanceRecord(
            student_id="S-102",
            status="Present",
            expected_zone="Classroom-B",
            expected_path=("Corridor-B", "Stairs-1"),
            recorded_at=now - timedelta(minutes=12),
        )
    ]

    alerts = evaluate_attendance_safety(attendance, [], timeframe_minutes=10, now=now)

    assert len(alerts) == 1
    assert alerts[0].severity == "critical"
    assert alerts[0].reason == "missing_from_camera_feeds"
    assert alerts[0].detected_zone is None
