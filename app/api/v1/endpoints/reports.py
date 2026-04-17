from fastapi import APIRouter
from datetime import datetime, timedelta

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/list")
def list_reports() -> list[dict[str, object]]:
    now = datetime.now()
    return [
        {"id": "rpt-001", "title": "Daily Operational Summary", "type": "operational", "period": "Today", "generated_at": now.strftime("%Y-%m-%d %H:%M"), "status": "ready"},
        {"id": "rpt-002", "title": "Weekly Incident Analysis", "type": "analytical", "period": "This Week", "generated_at": (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M"), "status": "ready"},
        {"id": "rpt-003", "title": "Monthly Safety Assessment", "type": "supervisory", "period": "March 2026", "generated_at": (now - timedelta(days=3)).strftime("%Y-%m-%d %H:%M"), "status": "ready"},
        {"id": "rpt-004", "title": "Q1 2026 Ministerial Report", "type": "ministerial", "period": "Q1 2026", "generated_at": (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M"), "status": "ready"},
        {"id": "rpt-005", "title": "Semester End Self-Assessment", "type": "supervisory", "period": "Sem 2 2025-2026", "generated_at": "Scheduled", "status": "scheduled"},
    ]


@router.get("/stats")
def report_stats() -> dict[str, object]:
    return {
        "weekly_incidents_by_day": [
            {"day": "Sun", "count": 4}, {"day": "Mon", "count": 2}, {"day": "Tue", "count": 6},
            {"day": "Wed", "count": 3}, {"day": "Thu", "count": 1}, {"day": "Fri", "count": 0}, {"day": "Sat", "count": 2},
        ],
        "top_risk_zones": [
            {"zone": "Learning Commons", "risk": 0.68, "incidents": 7},
            {"zone": "Corridor A", "risk": 0.52, "incidents": 5},
            {"zone": "Main Gate", "risk": 0.44, "incidents": 4},
            {"zone": "Playground", "risk": 0.31, "incidents": 2},
        ],
        "attendance_by_week": [
            {"week": "W1", "rate": 91.2}, {"week": "W2", "rate": 93.8}, {"week": "W3", "rate": 94.5},
            {"week": "W4", "rate": 92.1}, {"week": "W5", "rate": 94.2}, {"week": "W6", "rate": 95.0},
        ],
        "incident_types": [
            {"type": "Crowd Density", "count": 8, "color": "#e84d5b"},
            {"type": "Behavioral Anomaly", "count": 5, "color": "#ffb84d"},
            {"type": "Attendance Gap", "count": 3, "color": "#9b6dff"},
            {"type": "Path Deviation", "count": 2, "color": "#4f8fd8"},
        ],
    }
