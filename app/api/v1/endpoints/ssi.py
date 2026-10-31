"""School Safety Index endpoints with explicit school-owned history."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_school_id, require_teacher
from app.db.session import get_db
from app.services import ssi_history

router = APIRouter(prefix="/ssi", tags=["ssi"], dependencies=[Depends(require_teacher)])


@router.get("/live")
def ssi_live(school_id: str = Depends(get_current_school_id)) -> dict[str, object]:
    """Live SSI remains unavailable while its sensor/forecast inputs are shared."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "SCHOOL_SCOPED_SSI_LIVE_UNAVAILABLE",
            "message": "Live SSI is paused until sensor inputs and forecasts are partitioned by school.",
            "school_id": school_id,
        },
    )


@router.get("/history")
def ssi_history_endpoint(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> dict[str, object]:
    """Return only historical SSI snapshots assigned to the authenticated school."""
    return ssi_history.summarize(db, school_id, days)
