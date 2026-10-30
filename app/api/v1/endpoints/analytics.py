from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.api.deps import require_teacher

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(require_teacher)])


@router.get("/overview")
def analytics_overview() -> dict[str, object]:
    """Return an honest analytics contract until verified, tenant-owned feeds exist.

    Demo seed rows are deliberately not counted as operational evidence. Metrics
    remain unavailable rather than presenting seeded or unverified values as live.
    """
    unavailable_metrics = (
        "attendance_rate", "total_students", "active_cameras", "total_units",
        "incidents_today", "incidents_week", "avg_crowd_density",
        "peak_density_zone", "uptime_percent", "alerts_resolved_today",
        "patrol_efficiency", "compliance_score",
    )
    return {
        "data_status": "unavailable",
        "data_notice": (
            "Live analytics are not yet available. Demo seed records and "
            "unverified observations are excluded from operational metrics."
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": {
            key: {"value": None, "status": "unavailable", "source": None, "observed_at": None}
            for key in unavailable_metrics
        },
        **{key: None for key in unavailable_metrics},
    }
