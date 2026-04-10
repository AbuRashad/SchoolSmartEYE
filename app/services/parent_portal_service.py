from __future__ import annotations

from datetime import datetime

from app.services.attendance_safety_integration import (
    AttendanceRecord,
    SecurityGapAlert,
    StudentDetection,
    evaluate_attendance_safety,
)


class ParentPortalService:
    """Unit 12: Smart Parent Portal with strict privacy governance controls."""

    def __init__(
        self,
        parent_child_registry: dict[str, set[str]],
        designated_exit_gates: set[str] | None = None,
    ) -> None:
        self.parent_child_registry = parent_child_registry
        self.designated_exit_gates = designated_exit_gates or {"Main-Gate", "North-Gate"}

    def fetch_attendance_dismissal_status(
        self,
        parent_id: str,
        child_id: str,
        attendance_records: list[AttendanceRecord],
        detections: list[StudentDetection],
        now: datetime | None = None,
    ) -> dict[str, object]:
        """Return parent-eligible real-time attendance and dismissal status."""
        self._assert_parent_access(parent_id, child_id)

        child_attendance = self._latest_attendance(attendance_records, child_id)
        child_detection = self._latest_detection(detections, child_id)

        safety_alerts = evaluate_attendance_safety(
            attendance_records=[record for record in attendance_records if record.student_id == child_id],
            detections=[detection for detection in detections if detection.student_id == child_id],
            now=now,
        )

        safety_status = "safe"
        if safety_alerts:
            top_alert = self._highest_severity_alert(safety_alerts)
            safety_status = self._parent_safe_label(top_alert)

        dismissal_status = "not_at_exit_gate"
        if child_detection and child_detection.zone in self.designated_exit_gates:
            dismissal_status = "at_designated_exit_gate"

        return {
            "parent_id": parent_id,
            "student_id": child_id,
            "attendance_status": child_attendance.status if child_attendance else "unknown",
            "safety_status": safety_status,
            "dismissal_status": dismissal_status,
            "last_known_zone": child_detection.zone if child_detection else None,
            "last_updated": (child_detection.detected_at if child_detection else now).isoformat()
            if (child_detection or now)
            else None,
        }

    def trigger_parent_notifications(
        self,
        parent_id: str,
        child_id: str,
        attendance_records: list[AttendanceRecord],
        detections: list[StudentDetection],
        safety_alerts: list[SecurityGapAlert] | None = None,
    ) -> list[dict[str, object]]:
        """Generate privacy-filtered parent notifications for relevant events only."""
        self._assert_parent_access(parent_id, child_id)

        notifications: list[dict[str, object]] = []
        child_attendance = self._latest_attendance(attendance_records, child_id)
        child_detection = self._latest_detection(detections, child_id)

        if (
            child_attendance
            and child_attendance.status.strip().lower() == "present"
            and child_detection
            and child_detection.zone in self.designated_exit_gates
        ):
            notifications.append(
                {
                    "event_type": "dismissal_update",
                    "student_id": child_id,
                    "safety_status": "confirmed_on_correct_path",
                    "message": f"Student {child_id} detected at designated exit gate.",
                    "timestamp": child_detection.detected_at.isoformat(),
                }
            )

        for alert in safety_alerts or []:
            if alert.student_id != child_id:
                continue
            notifications.append(
                {
                    "event_type": "safety_alert",
                    "student_id": child_id,
                    "safety_status": self._parent_safe_label(alert),
                    "message": self._to_parent_message(alert),
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )

        return [self.privacy_filter_notification(item) for item in notifications]

    @staticmethod
    def privacy_filter_notification(notification_payload: dict[str, object]) -> dict[str, object]:
        """Remove admin-only technical signals before sending to parents."""
        blocked_fields = {
            "anomaly_coefficient",
            "detailed_scene_analysis",
            "raw_video_frame",
            "optical_flow_vectors",
            "face_embedding",
        }
        return {
            key: value
            for key, value in notification_payload.items()
            if key not in blocked_fields
        }

    def _assert_parent_access(self, parent_id: str, child_id: str) -> None:
        allowed_children = self.parent_child_registry.get(parent_id, set())
        if child_id not in allowed_children:
            raise PermissionError("Access denied: parent can only access linked child records")

    @staticmethod
    def _latest_attendance(records: list[AttendanceRecord], child_id: str) -> AttendanceRecord | None:
        candidates = [record for record in records if record.student_id == child_id]
        if not candidates:
            return None

        with_time = [record for record in candidates if record.recorded_at is not None]
        if with_time:
            return max(with_time, key=lambda record: record.recorded_at)
        return candidates[-1]

    @staticmethod
    def _latest_detection(detections: list[StudentDetection], child_id: str) -> StudentDetection | None:
        candidates = [detection for detection in detections if detection.student_id == child_id]
        if not candidates:
            return None
        return max(candidates, key=lambda detection: detection.detected_at)

    @staticmethod
    def _highest_severity_alert(alerts: list[SecurityGapAlert]) -> SecurityGapAlert:
        severity_rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
        return max(alerts, key=lambda alert: severity_rank.get(alert.severity.lower(), 0))

    @staticmethod
    def _parent_safe_label(alert: SecurityGapAlert) -> str:
        mapping = {
            "missing_from_camera_feeds": "attention_required",
            "restricted_zone_detected": "attention_required",
            "unexpected_zone": "monitoring_in_progress",
        }
        return mapping.get(alert.reason, "monitoring_in_progress")

    @staticmethod
    def _to_parent_message(alert: SecurityGapAlert) -> str:
        if alert.reason == "missing_from_camera_feeds":
            return "Student location is being verified by school safety staff."
        if alert.reason == "restricted_zone_detected":
            return "School safety team is guiding the student to an approved area."
        if alert.reason == "unexpected_zone":
            return "Student movement is being monitored to confirm safe route compliance."
        return "School safety team is reviewing a student movement update."
