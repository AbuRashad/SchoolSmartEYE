"""Mock student portal data for demonstration purposes."""

from fastapi import APIRouter

router = APIRouter(prefix="/portal", tags=["portal"])


@router.get("/student")
def get_student() -> dict[str, object]:
    return {
        "name": "Ahmed Al-Rashidi",
        "grade": "Grade 9 — Class A",
        "student_id": "STU-2024-0847",
        "photo_initial": "A",
        "attendance_today": "present",
        "arrival_time": "07:42 AM",
        "last_seen_zone": "Learning Commons",
        "dismissal_status": "Not at exit gate",
        "safety_status": "safe",
        "attendance_streak": 14,
        "monthly_attendance": 94.5,
        "notifications": [
            {"id": "n1", "type": "attendance", "message": "Ahmed arrived at school at 07:42 AM", "time": "07:42 AM", "read": True},
            {"id": "n2", "type": "safety", "message": "Ahmed is in Learning Commons — all clear", "time": "10:15 AM", "read": True},
            {"id": "n3", "type": "info", "message": "School Safety Index is above benchmark today", "time": "11:00 AM", "read": False},
            {"id": "n4", "type": "attendance", "message": "Lunch break started. Ahmed in cafeteria zone.", "time": "12:30 PM", "read": False},
        ],
        "weekly_attendance": [
            {"day": "Sun", "present": True}, {"day": "Mon", "present": True}, {"day": "Tue", "present": True},
            {"day": "Wed", "present": False}, {"day": "Thu", "present": True}, {"day": "Fri", "present": True},
            {"day": "Sat", "present": True},
        ],
    }
