from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_school_id, require_teacher

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(require_teacher)])


@router.get("/overview")
def analytics_overview(school_id: str = Depends(get_current_school_id)) -> dict[str, object]:
    """Do not present global illustrative metrics as a school's operational analytics."""
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "SCHOOL_SCOPED_ANALYTICS_UNAVAILABLE",
            "message": "Analytics are temporarily unavailable until their source records are school-scoped.",
            "school_id": school_id,
        },
    )
