"""School Safety Index history is scoped to the authenticated school.

Live SSI remains unavailable until sensor inputs, forecasts and runtime caches
are partitioned by school. Historical snapshots are safe to expose only via
school-filtered persistence.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_school_id, require_teacher
from app.db.session import get_db
from app.services import ssi_history

router = APIRouter(prefix="/ssi", tags=["ssi"], dependencies=[Depends(require_teacher)])


def _ssi_live_unavailable(school_id: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "SCHOOL_SCOPED_SSI_LIVE_UNAVAILABLE",
            "message": "Live SSI is paused until sensor inputs, forecasts, and runtime caches are partitioned by school.",
            "school_id": school_id,
        },
    )


@router.get("/live")
def ssi_live(school_id: str = Depends(get_current_school_id)) -> dict[str, object]:
    """Do not return simulated shared sensor signals as a school's live safety score."""
    _ssi_live_unavailable(school_id)


@router.get("/history")
def ssi_history_endpoint(
    days: int = Query(30, ge=1, le=365),
    school_id: str = Depends(get_current_school_id),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    """Return only SSI snapshots explicitly owned by the authenticated school."""
    return ssi_history.summarize(db, school_id, days)
