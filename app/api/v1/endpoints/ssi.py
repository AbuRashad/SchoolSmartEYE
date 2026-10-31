"""School Safety Index endpoints; unavailable until signals and snapshots are tenant-scoped."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_school_id, require_teacher

router = APIRouter(prefix="/ssi", tags=["ssi"], dependencies=[Depends(require_teacher)])


def _ssi_unavailable(school_id: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "SCHOOL_SCOPED_SSI_UNAVAILABLE",
            "message": "SSI is paused until sensor inputs, forecasts, and historical snapshots are scoped to this school.",
            "school_id": school_id,
        },
    )


@router.get("/live")
def ssi_live(school_id: str = Depends(get_current_school_id)) -> dict[str, object]:
    """Do not return simulated shared sensor signals as a school's live safety score."""
    _ssi_unavailable(school_id)


@router.get("/history")
def ssi_history_endpoint(
    days: int = Query(30, ge=1, le=365),
    school_id: str = Depends(get_current_school_id),
) -> dict[str, object]:
    """Historical SSI is withheld until each snapshot has verified school ownership."""
    _ssi_unavailable(school_id)
