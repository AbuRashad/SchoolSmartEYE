"""School-scoped incident management.

Incident ownership is inherited only through a persisted zone whose school_id
matches the authenticated membership. Unassigned legacy zones are inaccessible.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_school_id, get_current_user, require_principal, require_teacher
from app.db import models as orm
from app.db.session import get_db

router = APIRouter(prefix="/incidents", tags=["incidents"])


class IncidentCreate(BaseModel):
    incident_id: str = Field(..., min_length=1, max_length=64)
    zone_id: str = Field(..., min_length=1, max_length=64)
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    description: str = Field(..., min_length=1, max_length=512)


class IncidentOut(BaseModel):
    incident_id: str
    zone_id: str
    severity: str
    description: str
    detected_at: datetime
    resolved: bool
    resolved_at: datetime | None
    acknowledged_by: str | None


def _incident_query(school_id: str):
    return (
        select(orm.Incident)
        .join(orm.Zone, orm.Zone.zone_id == orm.Incident.zone_id)
        .where(orm.Zone.school_id == school_id)
    )


def _get_incident(db: Session, incident_id: str, school_id: str) -> orm.Incident:
    incident = db.scalar(
        _incident_query(school_id).where(orm.Incident.incident_id == incident_id)
    )
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


@router.get("", response_model=list[IncidentOut], dependencies=[Depends(require_teacher)])
def list_incidents(
    resolved: bool | None = None,
    severity: str | None = Query(default=None, pattern="^(low|medium|high|critical)$"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> list[IncidentOut]:
    stmt = _incident_query(school_id)
    if resolved is not None:
        stmt = stmt.where(orm.Incident.resolved.is_(resolved))
    if severity is not None:
        stmt = stmt.where(orm.Incident.severity == severity)
    rows = db.scalars(
        stmt.order_by(orm.Incident.detected_at.desc()).offset(offset).limit(limit)
    ).all()
    return [IncidentOut.model_validate(row, from_attributes=True) for row in rows]


@router.get("/{incident_id}", response_model=IncidentOut, dependencies=[Depends(require_teacher)])
def get_incident(
    incident_id: str,
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> IncidentOut:
    return IncidentOut.model_validate(_get_incident(db, incident_id, school_id), from_attributes=True)


@router.post(
    "",
    response_model=IncidentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_principal)],
)
def create_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> IncidentOut:
    zone = db.scalar(
        select(orm.Zone).where(
            orm.Zone.zone_id == payload.zone_id,
            orm.Zone.school_id == school_id,
        )
    )
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found in this school")
    if db.get(orm.Incident, payload.incident_id) is not None:
        raise HTTPException(status_code=409, detail="Incident ID already exists")
    incident = orm.Incident(
        incident_id=payload.incident_id,
        zone_id=zone.zone_id,
        severity=payload.severity,
        description=payload.description,
        detected_at=datetime.now(timezone.utc),
        resolved=False,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return IncidentOut.model_validate(incident, from_attributes=True)


@router.post(
    "/{incident_id}/resolve",
    response_model=IncidentOut,
    dependencies=[Depends(require_principal)],
)
def resolve_incident(
    incident_id: str,
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
    user: orm.User = Depends(get_current_user),
) -> IncidentOut:
    incident = _get_incident(db, incident_id, school_id)
    if not incident.resolved:
        incident.resolved = True
        incident.resolved_at = datetime.now(timezone.utc)
        incident.acknowledged_by = user.username
        db.commit()
        db.refresh(incident)
    return IncidentOut.model_validate(incident, from_attributes=True)
