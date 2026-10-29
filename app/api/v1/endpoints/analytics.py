from fastapi import APIRouter, Depends

from app.api.deps import require_teacher

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(require_teacher)])


@router.get("/overview")
def analytics_overview() -> dict[str, object]:
    return {
        "attendance_rate": 94.2,
        "total_students": 1247,
        "active_cameras": 12,
        "total_units": 14,
        "incidents_today": 3,
        "incidents_week": 18,
        "avg_crowd_density": 0.42,
        "peak_density_zone": "Learning Commons",
        "uptime_percent": 99.7,
        "alerts_resolved_today": 7,
        "patrol_efficiency": 88.5,
        "compliance_score": 96.1,
    }
