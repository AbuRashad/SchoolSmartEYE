from datetime import datetime, timedelta

import pytest

from app.services.attendance_safety_integration import AttendanceRecord, StudentDetection
from app.services.parent_portal_service import ParentPortalService


def test_access_control_parent_cannot_access_other_student_data() -> None:
    service = ParentPortalService(parent_child_registry={"parent-a": {"student-a"}})
    now = datetime(2026, 4, 6, 12, 0)

    attendance = [
        AttendanceRecord(
            student_id="student-b",
            status="Present",
            expected_zone="Classroom-B",
            recorded_at=now,
        )
    ]
    detections = [
        StudentDetection(student_id="student-b", zone="Classroom-B", detected_at=now)
    ]

    with pytest.raises(PermissionError):
        service.fetch_attendance_dismissal_status(
            parent_id="parent-a",
            child_id="student-b",
            attendance_records=attendance,
            detections=detections,
            now=now,
        )


def test_notification_triggered_at_designated_exit_gate() -> None:
    service = ParentPortalService(
        parent_child_registry={"parent-a": {"student-a"}},
        designated_exit_gates={"Main-Gate"},
    )
    now = datetime(2026, 4, 6, 13, 30)

    attendance = [
        AttendanceRecord(
            student_id="student-a",
            status="Present",
            expected_zone="Classroom-A",
            expected_path=("Corridor-A", "Main-Gate"),
            recorded_at=now - timedelta(minutes=20),
        )
    ]
    detections = [
        StudentDetection(
            student_id="student-a",
            zone="Main-Gate",
            detected_at=now,
        )
    ]

    notifications = service.trigger_parent_notifications(
        parent_id="parent-a",
        child_id="student-a",
        attendance_records=attendance,
        detections=detections,
    )

    assert len(notifications) == 1
    assert notifications[0]["event_type"] == "dismissal_update"
    assert notifications[0]["safety_status"] == "confirmed_on_correct_path"


def test_privacy_filter_hides_detailed_scene_analysis_from_parents() -> None:
    payload = {
        "event_type": "safety_alert",
        "student_id": "student-a",
        "safety_status": "monitoring_in_progress",
        "message": "School safety team is reviewing a student movement update.",
        "anomaly_coefficient": 0.91,
        "detailed_scene_analysis": {"vector_entropy": 0.87},
    }

    filtered = ParentPortalService.privacy_filter_notification(payload)

    assert filtered["event_type"] == "safety_alert"
    assert filtered["student_id"] == "student-a"
    assert filtered["safety_status"] == "monitoring_in_progress"
    assert "anomaly_coefficient" not in filtered
    assert "detailed_scene_analysis" not in filtered
