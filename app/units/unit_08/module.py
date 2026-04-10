"""Unit 08: Attendance-Safety Integration — wraps attendance service as a named unit."""
from __future__ import annotations

from app.services.attendance_safety_integration import (
    AttendanceRecord,
    StudentDetection,
    SecurityGapAlert,
    evaluate_attendance_safety,
)

UNIT_08_NAME = "Attendance & Safety Integration Unit"

__all__ = [
    "UNIT_08_NAME",
    "AttendanceRecord",
    "StudentDetection",
    "SecurityGapAlert",
    "evaluate_attendance_safety",
]
