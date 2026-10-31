"""School-scoped emergency drill management."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_school_id, require_principal, require_teacher
from app.db import models as orm
from app.db.session import get_db

router = APIRouter(prefix="/drills", tags=["drills"])


class DrillCreate(BaseModel):
    drill_id: str = Field(..., min_length=1, max_length=64)
    drill_type: str = Field(..., min_length=1, max_length=32)
    scheduled_at: datetime
    notes: str = Field(default="", max_length=512)


class DrillOut(BaseModel):
    drill_id: str
    drill_type: str
    scheduled_at: datetime
    completed: bool
    completed_at: datetime | None
    response_time_seconds: float | None
    notes: str


class DrillCompletion(BaseModel):
    response_time_seconds: float | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=512)


def _get_drill(db: Session, drill_id: str, school_id: str) -> orm.Drill:
    drill = db.scalar(
        select(orm.Drill).where(
            orm.Drill.drill_id == drill_id,
            orm.Drill.school_id == school_id,
        )
    )
    if drill is None:
        raise HTTPException(status_code=404, detail="Drill not found")
    return drill


@router.get("", response_model=list[DrillOut], dependencies=[Depends(require_teacher)])
def list_drills(
    completed: bool | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> list[DrillOut]:
    stmt = select(orm.Drill).where(orm.Drill.school_id == school_id)
    if completed is not None:
        stmt = stmt.where(orm.Drill.completed.is_(completed))
    rows = db.scalars(
        stmt.order_by(orm.Drill.scheduled_at.desc()).offset(offset).limit(limit)
    ).all()
    return [DrillOut.model_validate(row, from_attributes=True) for row in rows]


@router.get("/{drill_id}", response_model=DrillOut, dependencies=[Depends(require_teacher)])
def get_drill(
    drill_id: str,
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> DrillOut:
    return DrillOut.model_validate(_get_drill(db, drill_id, school_id), from_attributes=True)


@router.post(
    "",
    response_model=DrillOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_principal)],
)
def create_drill(
    payload: DrillCreate,
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> DrillOut:
    if db.get(orm.Drill, payload.drill_id) is not None:
        raise HTTPException(status_code=409, detail="Drill ID already exists")
    drill = orm.Drill(
        drill_id=payload.drill_id,
        school_id=school_id,
        drill_type=payload.drill_type,
        scheduled_at=payload.scheduled_at,
        completed=False,
        notes=payload.notes,
    )
    db.add(drill)
    db.commit()
    db.refresh(drill)
    return DrillOut.model_validate(drill, from_attributes=True)


@router.patch(
    "/{drill_id}/complete",
    response_model=DrillOut,
    dependencies=[Depends(require_principal)],
)
def complete_drill(
    drill_id: str,
    payload: DrillCompletion,
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> DrillOut:
    drill = _get_drill(db, drill_id, school_id)
    if not drill.completed:
        drill.completed = True
        drill.completed_at = datetime.now(timezone.utc)
    if payload.response_time_seconds is not None:
        drill.response_time_seconds = payload.response_time_seconds
    if payload.notes is not None:
        drill.notes = payload.notes
    db.commit()
    db.refresh(drill)
    return DrillOut.model_validate(drill, from_attributes=True)
