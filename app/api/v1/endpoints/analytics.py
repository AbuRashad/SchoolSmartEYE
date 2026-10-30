from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_teacher, school_scope
from app.db.models import User
from app.db.session import get_db
from app.services.verified_analytics import camera_analytics

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(require_teacher)])

_UNAVAILABLE_KEYS = (
    "attendance_rate", "total_students", "incidents_today", "incidents_week",
    "avg_crowd_density", "peak_density_zone", "alerts_resolved_today",
    "patrol_efficiency", "compliance_score",
)


@router.get("/overview")
def analytics_overview(
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
) -> dict[str, object]:
    """Return verified camera metrics and explicitly unavailable unsupported metrics.

    School accounts are restricted to their own tenant. Ministry receives only
    aggregate counts across tenants; no school, camera, or student identifiers.
    """
    camera_metrics = camera_analytics(db, school_id=school_scope(user))
    metrics: dict[str, dict[str, object]] = {
        key: {"value": None, "status": "unavailable", "source": None, "observed_at": None}
        for key in _UNAVAILABLE_KEYS
    }
    metrics.update(camera_metrics)
    available_count = sum(metric["status"] == "live" for metric in metrics.values())
    all_count = len(metrics)
    data_status = "partial" if available_count else "unavailable"
    if data_status == "partial":
        notice = (
            "Only camera health metrics backed by authenticated, fresh edge-agent telemetry are available. "
            "Other metrics remain unavailable until their source and verification pipelines are implemented."
        )
    else:
        notice = (
            "Live analytics are not yet available. No fresh authenticated edge-agent telemetry was found; "
            "demo seed records and principal-reported snapshots are excluded."
        )
    values = {key: metric["value"] for key, metric in metrics.items()}
    return {
        "data_status": data_status,
        "data_notice": notice,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
        **values,
    }
