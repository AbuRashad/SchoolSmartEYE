"""Student bracelet CRUD + heartbeat simulation.

A bracelet is a wearable tracker assigned 1:1 to a student. This endpoint is
hardware-agnostic — any BLE / LoRa / RFID / GPS tag gateway can POST heartbeats
to `/{bracelet_id}/ping` to update battery & last-seen-zone.
"""
from __future__ import annotations

import re
import threading
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator

from app.models import Bracelet
from app.services import seed_data

router = APIRouter(prefix="/bracelets", tags=["control"])

_lock = threading.Lock()

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


def _find(bracelet_id: str) -> Bracelet | None:
    return next((b for b in seed_data.bracelets if b.bracelet_id == bracelet_id), None)


def _student_name(student_id: str) -> str | None:
    s = next((s for s in seed_data.students if s.student_id == student_id), None)
    return s.name if s else None


def _low_battery_threshold() -> int:
    # Local import to avoid a circular import at module load.
    from app.core.runtime_settings import get_runtime_settings
    return get_runtime_settings().bracelet_low_battery_percent


def _serialize(b: Bracelet) -> BraceletOut:
    threshold = _low_battery_threshold()
    return BraceletOut(
        bracelet_id=b.bracelet_id,
        student_id=b.student_id,
        student_name=_student_name(b.student_id),
        mac_address=b.mac_address,
        battery_level=b.battery_level,
        is_active=b.is_active,
        last_seen_zone=b.last_seen_zone,
        last_seen_at=b.last_seen_at.isoformat() if b.last_seen_at else None,
        firmware_version=b.firmware_version,
        notes=b.notes,
        low_battery=b.battery_level <= threshold,
    )


def _student_exists(student_id: str) -> bool:
    return any(s.student_id == student_id for s in seed_data.students)


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("", response_model=list[BraceletOut])
def list_bracelets() -> list[BraceletOut]:
    with _lock:
        return [_serialize(b) for b in seed_data.bracelets]


@router.post("", response_model=BraceletOut, status_code=status.HTTP_201_CREATED)
def create_bracelet(payload: BraceletCreate) -> BraceletOut:
    with _lock:
        if _find(payload.bracelet_id) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Bracelet {payload.bracelet_id!r} already exists",
            )
        if not _student_exists(payload.student_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Student {payload.student_id!r} does not exist — add the student first",
            )
        # Enforce uniqueness of student_id (1 bracelet per student) and MAC
        if any(b.student_id == payload.student_id for b in seed_data.bracelets):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Student {payload.student_id!r} already has a bracelet assigned",
            )
        if any(b.mac_address == payload.mac_address for b in seed_data.bracelets):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"MAC address {payload.mac_address!r} is already registered",
            )

        bracelet = Bracelet(
            bracelet_id=payload.bracelet_id,
            student_id=payload.student_id,
            mac_address=payload.mac_address,
            battery_level=payload.battery_level,
            is_active=payload.is_active,
            firmware_version=payload.firmware_version,
            notes=payload.notes,
        )
        seed_data.bracelets.append(bracelet)
        return _serialize(bracelet)


@router.patch("/{bracelet_id}", response_model=BraceletOut)
def update_bracelet(bracelet_id: str, payload: BraceletUpdate) -> BraceletOut:
    with _lock:
        bracelet = _find(bracelet_id)
        if bracelet is None:
            raise HTTPException(status_code=404, detail=f"Bracelet {bracelet_id!r} not found")

        if payload.student_id is not None and payload.student_id != bracelet.student_id:
            if not _student_exists(payload.student_id):
                raise HTTPException(status_code=400, detail=f"Student {payload.student_id!r} does not exist")
            if any(b.student_id == payload.student_id and b.bracelet_id != bracelet_id for b in seed_data.bracelets):
                raise HTTPException(
                    status_code=409,
                    detail=f"Student {payload.student_id!r} already has a bracelet assigned",
                )
            bracelet.student_id = payload.student_id

        if payload.mac_address is not None and payload.mac_address != bracelet.mac_address:
            if any(b.mac_address == payload.mac_address and b.bracelet_id != bracelet_id for b in seed_data.bracelets):
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

        return _serialize(bracelet)


@router.delete("/{bracelet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bracelet(bracelet_id: str) -> Response:
    with _lock:
        bracelet = _find(bracelet_id)
        if bracelet is None:
            raise HTTPException(status_code=404, detail=f"Bracelet {bracelet_id!r} not found")
        seed_data.bracelets.remove(bracelet)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{bracelet_id}/ping", response_model=BraceletOut)
def ping_bracelet(bracelet_id: str, payload: BraceletPing) -> BraceletOut:
    """Simulate a BLE/LoRa gateway heartbeat for this bracelet.

    Updates `last_seen_zone`, `last_seen_at`, and optionally `battery_level`.
    A real-world gateway would POST this payload whenever it observes the tag.
    """
    with _lock:
        bracelet = _find(bracelet_id)
        if bracelet is None:
            raise HTTPException(status_code=404, detail=f"Bracelet {bracelet_id!r} not found")
        # Zone must exist (light validation)
        if not any(z.zone_id == payload.zone_id for z in seed_data.zones):
            raise HTTPException(status_code=400, detail=f"Zone {payload.zone_id!r} does not exist")
        bracelet.last_seen_zone = payload.zone_id
        bracelet.last_seen_at = datetime.now(timezone.utc)
        if payload.battery_level is not None:
            bracelet.battery_level = payload.battery_level
        return _serialize(bracelet)
