"""Early-warning attendance risk scoring (teacher+)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_teacher
from app.db import models as orm
from app.db.session import get_db
from app.services import attendance_risk

router = APIRouter(prefix="/risk", tags=["risk"], dependencies=[Depends(require_teacher)])


@router.get("/attendance")
def school_attendance_risk(
    min_level: str = Query("low", pattern="^(low|medium|high)$"),
    window_days: int = Query(14, ge=3, le=60),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    rank = {"low": 0, "medium": 1, "high": 2}
    rows = [
        r for r in attendance_risk.school_risk(db, window_days)
        if rank[str(r["risk_level"])] >= rank[min_level]
    ]
    return {"students": rows, "total": len(rows)}


@router.get("/attendance/{student_id}")
def student_attendance_risk(
    student_id: str, window_days: int = Query(14, ge=3, le=60), db: Session = Depends(get_db)
) -> dict[str, object]:
    if db.get(orm.Student, student_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Student {student_id!r} not found")
    return attendance_risk.student_risk(db, student_id, window_days)
