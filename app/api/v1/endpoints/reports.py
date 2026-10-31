from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_school_id, require_ministry

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_ministry)])


def _reports_unavailable(school_id: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail={
            "code": "SCHOOL_SCOPED_REPORTS_UNAVAILABLE",
            "message": "Reports are temporarily unavailable until operational source records are school-scoped.",
            "school_id": school_id,
        },
    )


@router.get("/list")
def list_reports(school_id: str = Depends(get_current_school_id)) -> list[dict[str, object]]:
    _reports_unavailable(school_id)


@router.get("/stats")
def report_stats(school_id: str = Depends(get_current_school_id)) -> dict[str, object]:
    _reports_unavailable(school_id)
