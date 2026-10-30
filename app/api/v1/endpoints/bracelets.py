"""Student bracelet CRUD + heartbeat simulation.

A bracelet is a wearable tracker assigned 1:1 to a student. This endpoint is
hardware-agnostic — any BLE / LoRa / RFID / GPS tag gateway can POST heartbeats
to `/{bracelet_id}/ping` to update battery & last-seen-zone.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_principal, require_teacher
from app.db import models as orm
from app.db.session import get_db

router = APIRouter(prefix="/bracelets", tags=["control"])

_MAC_RE = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}$")


# ── Schemas ───────────────────────────────────────────────────────────────────


class BraceletOut(BaseModel):
    bracelet_id: str
    student_id: str
    student_name: str | None
    mac_address: str
    battery_level: int
    is_active: bool
    last_seen_zone: str | None
    last_seen_at: str | None
    firmware_version: str
    notes: str
    low_battery: bool


class BraceletCreate(BaseModel):
    bracelet_id: str = Field(..., min_length=1, max_length=64)
    student_id: str = Field(..., min_length=1, max_length=64)
    mac_address: str = Field(..., min_length=11, max_length=32)
    battery_level: int = Field(default=100, ge=0, le=100)
    firmware_version: str = Field(default="1.0.0", max_length=32)
    notes: str = Field(default="", max_length=256)
    is_active: bool = Field(default=True)

    @field_validator("mac_address")
    @classmethod
    def _check_mac(cls, value: str) -> str:
        if not _MAC_RE.match(value):
            raise ValueError("mac_address must be in the form AA:BB:CC:DD:EE:FF")
        return value.upper().replace("-", ":")


class BraceletUpdate(BaseModel):
    student_id: str | None = None
    mac_address: str | None = None
    battery_level: int | None = Field(default=None, ge=0, le=100)
    firmware_version: str | None = None
    notes: str | None = None
    is_active: bool | None = None

    @field_validator("mac_address")
    @classmethod
    def _check_mac(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _MAC_RE.match(value):
            raise ValueError("mac_address must be in the form AA:BB:CC:DD:EE:FF")
        return value.upper().replace("-", ":")


class BraceletPing(BaseModel):
    """Payload a hardware gateway can POST when a bracelet is seen."""
    zone_id: str = Field(..., min_length=1)
    battery_level: int | None = Field(default=None, ge=0, le=100)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _school_id(user: orm.User) -> str:
    if not user.school_id:
        raise HTTPException(status_code=403, detail="A school-scoped account is required")
    return user.school_id


def _find(db: Session, bracelet_id: str, school_id: str) -> orm.Bracelet | None:
    return db.scalar(
        select(orm.Bracelet)
        .join(orm.Student, orm.Student.student_id == orm.Bracelet.student_id)
        .where(
            orm.Bracelet.bracelet_id == bracelet_id,
            orm.Student.school_id == school_id,
        )
    )


def _low_battery_threshold() -> int:
    # Local import to avoid a circular import at module load.
    from app.core.runtime_settings import get_runtime_settings
    return get_runtime_settings().bracelet_low_battery_percent


def _serialize(b: orm.Bracelet) -> BraceletOut:
    threshold = _low_battery_threshold()
    return BraceletOut(
        bracelet_id=b.bracelet_id,
        student_id=b.student_id,
        student_name=b.student.name if b.student else None,
        mac_address=b.mac_address,
        battery_level=b.battery_level,
        is_active=b.is_active,
        last_seen_zone=b.last_seen_zone,
        last_seen_at=b.last_seen_at.isoformat() if b.last_seen_at else None,
        firmware_version=b.firmware_version,
        notes=b.notes,
        low_battery=b.battery_level <= threshold,
    )


def _student_exists(db: Session, student_id: str, school_id: str) -> bool:
    return db.scalar(
        select(orm.Student.student_id).where(
            orm.Student.student_id == student_id,
            orm.Student.school_id == school_id,
        )
    ) is not None


def _student_has_other_bracelet(
    db: Session, student_id: str, bracelet_id: str | None, school_id: str
) -> bool:
    stmt = (
        select(orm.Bracelet.bracelet_id)
        .join(orm.Student, orm.Student.student_id == orm.Bracelet.student_id)
        .where(orm.Bracelet.student_id == student_id, orm.Student.school_id == school_id)
    )
    if bracelet_id is not None:
        stmt = stmt.where(orm.Bracelet.bracelet_id != bracelet_id)
    return db.scalar(stmt) is not None


def _mac_in_use(db: Session, mac: str, bracelet_id: str | None) -> bool:
    stmt = select(orm.Bracelet.bracelet_id).where(orm.Bracelet.mac_address == mac)
    if bracelet_id is not None:
        stmt = stmt.where(orm.Bracelet.bracelet_id != bracelet_id)
    return db.scalar(stmt) is not None


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("", response_model=list[BraceletOut])
def list_bracelets(
    db: Session = Depends(get_db), user: orm.User = Depends(require_teacher)
) -> list[BraceletOut]:
    school_id = _school_id(user)
    rows = db.scalars(
        select(orm.Bracelet)
        .join(orm.Student, orm.Student.student_id == orm.Bracelet.student_id)
        .where(orm.Student.school_id == school_id)
        .order_by(orm.Bracelet.bracelet_id)
    ).all()
    return [_serialize(b) for b in rows]


@router.post(
    "",
    response_model=BraceletOut,
    status_code=status.HTTP_201_CREATED,
 )
def create_bracelet(
    payload: BraceletCreate,
    db: Session = Depends(get_db),
    user: orm.User = Depends(require_principal),
) -> BraceletOut:
    school_id = _school_id(user)
    if _find(db, payload.bracelet_id, school_id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Bracelet {payload.bracelet_id!r} already exists",
        )
    if not _student_exists(db, payload.student_id, school_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student {payload.student_id!r} does not exist — add the student first",
        )
    # Enforce uniqueness of student_id (1 bracelet per student) and MAC
    if _student_has_other_bracelet(db, payload.student_id, None, school_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Student {payload.student_id!r} already has a bracelet assigned",
        )
    if _mac_in_use(db, payload.mac_address, None):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"MAC address {payload.mac_address!r} is already registered",
        )

    bracelet = orm.Bracelet(
        bracelet_id=payload.bracelet_id,
        student_id=payload.student_id,
        mac_address=payload.mac_address,
        battery_level=payload.battery_level,
        is_active=payload.is_active,
        firmware_version=payload.firmware_version,
        notes=payload.notes,
    )
    db.add(bracelet)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Bracelet conflicts with an existing record") from None
    return _serialize(bracelet)


@router.patch("/{bracelet_id}", response_model=BraceletOut)
def update_bracelet(
    bracelet_id: str,
    payload: BraceletUpdate,
    db: Session = Depends(get_db),
    user: orm.User = Depends(require_principal),
) -> BraceletOut:
    school_id = _school_id(user)
    bracelet = _find(db, bracelet_id, school_id)
    if bracelet is None:
        raise HTTPException(status_code=404, detail=f"Bracelet {bracelet_id!r} not found")

    if payload.student_id is not None and payload.student_id != bracelet.student_id:
        if not _student_exists(db, payload.student_id, school_id):
            raise HTTPException(status_code=400, detail=f"Student {payload.student_id!r} does not exist")
        if _student_has_other_bracelet(db, payload.student_id, bracelet_id, school_id):
            raise HTTPException(
                status_code=409,
                detail=f"Student {payload.student_id!r} already has a bracelet assigned",
            )
        bracelet.student_id = payload.student_id

    if payload.mac_address is not None and payload.mac_address != bracelet.mac_address:
        if _mac_in_use(db, payload.mac_address, bracelet_id):
            raise HTTPException(status_code=409, detail="MAC address already in use")
        bracelet.mac_address = payload.mac_address

    if payload.battery_level is not None:
        bracelet.battery_level = payload.battery_level
    if payload.firmware_version is not None:
        bracelet.firmware_version = payload.firmware_version
    if payload.notes is not None:
        bracelet.notes = payload.notes
    if payload.is_active is not None:
        bracelet.is_active = payload.is_active

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Bracelet conflicts with an existing record") from None
    db.refresh(bracelet)
    return _serialize(bracelet)


@router.delete(
    "/{bracelet_id}",
    status_code=status.HTTP_204_NO_CONTENT,
 )
def delete_bracelet(
    bracelet_id: str,
    db: Session = Depends(get_db),
    user: orm.User = Depends(require_principal),
) -> Response:
    bracelet = _find(db, bracelet_id, _school_id(user))
    if bracelet is None:
        raise HTTPException(status_code=404, detail=f"Bracelet {bracelet_id!r} not found")
    db.delete(bracelet)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{bracelet_id}/ping", response_model=BraceletOut)
def ping_bracelet(
    bracelet_id: str,
    payload: BraceletPing,
    db: Session = Depends(get_db),
    user: orm.User = Depends(require_principal),
) -> BraceletOut:
    """Simulate a BLE/LoRa gateway heartbeat for this bracelet.

    Updates `last_seen_zone`, `last_seen_at`, and optionally `battery_level`.
    A real-world gateway would POST this payload whenever it observes the tag.
    """
    bracelet = _find(db, bracelet_id, _school_id(user))
    if bracelet is None:
        raise HTTPException(status_code=404, detail=f"Bracelet {bracelet_id!r} not found")
    # Zone must exist (light validation)
    zone = db.get(orm.Zone, payload.zone_id)
    if zone is None or zone.school_id != _school_id(user):
        raise HTTPException(status_code=400, detail=f"Zone {payload.zone_id!r} is not available in this school")
    bracelet.last_seen_zone = payload.zone_id
    bracelet.last_seen_at = datetime.now(timezone.utc)
    if payload.battery_level is not None:
        bracelet.battery_level = payload.battery_level
    db.commit()
    return _serialize(bracelet)
