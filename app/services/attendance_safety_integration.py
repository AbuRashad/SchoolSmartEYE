from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass(frozen=True)
class AttendanceRecord:
    student_id: str
    status: str
    expected_zone: str
    expected_path: tuple[str, ...] = field(default_factory=tuple)
    recorded_at: datetime | None = None


@dataclass(frozen=True)
class StudentDetection:
    student_id: str
    zone: str
    detected_at: datetime


@dataclass(frozen=True)
class SecurityGapAlert:
    student_id: str
    severity: str
    reason: str
    expected_zone: str
    detected_zone: str | None
    message: str


def evaluate_attendance_safety(
    attendance_records: list[AttendanceRecord],
    detections: list[StudentDetection],
    restricted_zones: set[str] | None = None,
    timeframe_minutes: int = 10,
    now: datetime | None = None,
) -> list[SecurityGapAlert]:
    """Compare attendance presence with live detections and flag safety gaps.

    A present student is considered safe when they are detected within the
    expected zone or along the approved path inside the configured timeframe.
    """
    if timeframe_minutes <= 0:
        raise ValueError("timeframe_minutes must be greater than zero")

    restricted_zones = restricted_zones or set()
    reference_time = now or _latest_reference_time(attendance_records, detections)
    window_start = reference_time - timedelta(minutes=timeframe_minutes)

    latest_detections: dict[str, StudentDetection] = {}
    for detection in detections:
        if detection.detected_at < window_start:
            continue

        previous = latest_detections.get(detection.student_id)
        if previous is None or detection.detected_at > previous.detected_at:
            latest_detections[detection.student_id] = detection

    alerts: list[SecurityGapAlert] = []
    for record in attendance_records:
        if record.status.strip().lower() != "present":
            continue

        detection = latest_detections.get(record.student_id)
        allowed_zones = {record.expected_zone, *record.expected_path}

        if detection is None:
            alerts.append(
                SecurityGapAlert(
                    student_id=record.student_id,
                    severity="critical",
                    reason="missing_from_camera_feeds",
                    expected_zone=record.expected_zone,
                    detected_zone=None,
                    message=(
                        f"Student {record.student_id} is marked Present but was not detected "
                        "within the expected timeframe."
                    ),
                )
            )
            continue

        if detection.zone in restricted_zones:
            alerts.append(
                SecurityGapAlert(
                    student_id=record.student_id,
                    severity="high",
                    reason="restricted_zone_detected",
                    expected_zone=record.expected_zone,
                    detected_zone=detection.zone,
                    message=(
                        f"Student {record.student_id} is marked Present but was detected in "
                        f"restricted zone {detection.zone}."
                    ),
                )
            )
            continue

        if detection.zone not in allowed_zones:
            alerts.append(
                SecurityGapAlert(
                    student_id=record.student_id,
                    severity="medium",
                    reason="unexpected_zone",
                    expected_zone=record.expected_zone,
                    detected_zone=detection.zone,
                    message=(
                        f"Student {record.student_id} is marked Present but is outside the "
                        "expected zone or approved path."
                    ),
                )
            )

    return alerts


def _latest_reference_time(
    attendance_records: list[AttendanceRecord],
    detections: list[StudentDetection],
) -> datetime:
    candidates = [detection.detected_at for detection in detections]
    candidates.extend(
        record.recorded_at for record in attendance_records if record.recorded_at is not None
    )

    if not candidates:
        raise ValueError("Cannot evaluate attendance safety without a reference timestamp")

    return max(candidates)
