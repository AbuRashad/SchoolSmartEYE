"""School-scoped live camera REST and MJPEG endpoints."""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_school_id,
    require_principal,
    require_teacher,
    require_teacher_stream,
    resolve_school_scope,
    role_of,
)
from app.core.governance_layer import SCOPE_LEVEL, Role
from app.db.models import Camera, User, Zone
from app.db.session import get_db
from app.services.camera_ingestion import CameraSource, ingestion_service
from app.units.unit_01.module import StreamStatus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cameras", tags=["cameras"])
_MJPEG_BOUNDARY = "frame"


class CameraCreate(BaseModel):
    camera_id: str = Field(..., min_length=1, max_length=64)
    zone_id: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1, max_length=128)
    source_url: str = Field(..., min_length=1)
    anonymize_faces: bool = True


class CameraInfo(BaseModel):
    camera_id: str
    zone_id: str
    label: str
    source_url: str
    anonymize_faces: bool
    status: str
    is_running: bool
    last_frame_at: str | None
    total_frames_captured: int
    drop_rate: float
    last_error: str | None


def _camera_record(db: Session, camera_id: str, school_id: str) -> Camera | None:
    return db.scalar(
        select(Camera)
        .join(Zone, Zone.zone_id == Camera.zone_id)
        .where(Camera.camera_id == camera_id, Zone.school_id == school_id)
    )


def _require_school_zone(db: Session, zone_id: str, school_id: str) -> Zone:
    zone = db.scalar(
        select(Zone).where(Zone.zone_id == zone_id, Zone.school_id == school_id)
    )
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found in this school")
    return zone


def _info_for(camera_id: str) -> CameraInfo | None:
    worker = ingestion_service.get_worker(camera_id)
    source = next((s for s in ingestion_service.list_sources() if s.camera_id == camera_id), None)
    stream = ingestion_service.capture_unit.get_stream(camera_id)
    if worker is None or source is None or stream is None:
        return None
    return CameraInfo(
        camera_id=source.camera_id,
        zone_id=source.zone_id,
        label=source.label,
        source_url=source.source_url,
        anonymize_faces=source.anonymize_faces,
        status=stream.status.value,
        is_running=worker.is_running,
        last_frame_at=stream.last_frame_at.isoformat() if stream.last_frame_at else None,
        total_frames_captured=stream.total_frames_captured,
        drop_rate=round(stream.drop_rate, 4),
        last_error=stream.last_error,
    )


@router.get("", response_model=list[CameraInfo])
def list_cameras(
    user: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> list[CameraInfo]:
    school_id = resolve_school_scope(db, user)
    owned_ids = set(
        db.scalars(
            select(Camera.camera_id)
            .join(Zone, Zone.zone_id == Camera.zone_id)
            .where(Zone.school_id == school_id, Camera.is_active.is_(True))
        )
    )
    role = role_of(user)
    can_see_source = role is not None and SCOPE_LEVEL[role] >= SCOPE_LEVEL[Role.PRINCIPAL]
    output: list[CameraInfo] = []
    for source in ingestion_service.list_sources():
        if source.camera_id not in owned_ids:
            continue
        info = _info_for(source.camera_id)
        if info is not None:
            output.append(
                info if can_see_source else info.model_copy(update={"source_url": "hidden"})
            )
    return output


@router.post(
    "",
    response_model=CameraInfo,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_principal)],
)
def register_camera(
    payload: CameraCreate,
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> CameraInfo:
    _require_school_zone(db, payload.zone_id, school_id)
    # Camera IDs are globally unique in the current schema. Do not query another tenant's row.
    source = CameraSource(
        camera_id=payload.camera_id,
        zone_id=payload.zone_id,
        label=payload.label,
        source_url=payload.source_url,
        anonymize_faces=payload.anonymize_faces,
    )
    record = Camera(
        camera_id=payload.camera_id,
        zone_id=payload.zone_id,
        label=payload.label,
        is_active=True,
    )
    db.add(record)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Camera could not be registered because its identifier or submitted data conflicts with an existing record.",
        ) from None
    try:
        ingestion_service.register(source, autostart=True)
        db.commit()
    except Exception:
        db.rollback()
        ingestion_service.unregister(payload.camera_id)
        raise
    info = _info_for(payload.camera_id)
    if info is None:
        raise HTTPException(status_code=500, detail="Camera registration failed")
    return info


@router.delete(
    "/{camera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_principal)],
)
def unregister_camera(
    camera_id: str,
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> Response:
    record = _camera_record(db, camera_id, school_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} not found")
    ingestion_service.unregister(camera_id)
    db.delete(record)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{camera_id}/start",
    response_model=CameraInfo,
    dependencies=[Depends(require_principal)],
)
def start_camera(
    camera_id: str,
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> CameraInfo:
    if _camera_record(db, camera_id, school_id) is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} not found")
    worker = ingestion_service.get_worker(camera_id)
    if worker is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} is not loaded")
    worker.start()
    info = _info_for(camera_id)
    assert info is not None
    return info


@router.post(
    "/{camera_id}/stop",
    response_model=CameraInfo,
    dependencies=[Depends(require_principal)],
)
def stop_camera(
    camera_id: str,
    db: Session = Depends(get_db),
    school_id: str = Depends(get_current_school_id),
) -> CameraInfo:
    if _camera_record(db, camera_id, school_id) is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} not found")
    worker = ingestion_service.get_worker(camera_id)
    if worker is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} is not loaded")
    worker.stop()
    stream = ingestion_service.capture_unit.get_stream(camera_id)
    if stream is not None:
        stream.status = StreamStatus.OFFLINE
    info = _info_for(camera_id)
    assert info is not None
    return info


@router.get(
    "/{camera_id}/snapshot.jpg",
    responses={200: {"content": {"image/jpeg": {}}}, 404: {}, 503: {}},
)
def snapshot(
    camera_id: str,
    user: User = Depends(require_teacher_stream),
    db: Session = Depends(get_db),
) -> Response:
    school_id = resolve_school_scope(db, user)
    if _camera_record(db, camera_id, school_id) is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} not found")
    worker = ingestion_service.get_worker(camera_id)
    if worker is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} is not loaded")
    jpeg = worker.get_latest_jpeg()
    if jpeg is None:
        raise HTTPException(status_code=503, detail="No frame is currently available")
    return Response(
        content=jpeg,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"},
    )


async def _mjpeg_generator(camera_id: str) -> AsyncIterator[bytes]:
    boundary = f"--{_MJPEG_BOUNDARY}\r\n".encode("ascii")
    worker = ingestion_service.get_worker(camera_id)
    if worker is None:
        return
    last_frame_id = id(None)
    while True:
        jpeg = await asyncio.to_thread(worker.wait_next_frame, 5.0)
        if jpeg is None or id(jpeg) == last_frame_id:
            await asyncio.sleep(0.05)
            continue
        last_frame_id = id(jpeg)
        yield boundary
        yield (
            f"Content-Type: image/jpeg\r\n"
            f"Content-Length: {len(jpeg)}\r\n\r\n"
        ).encode("ascii")
        yield jpeg
        yield b"\r\n"


@router.get(
    "/{camera_id}/stream.mjpg",
    responses={200: {"content": {"multipart/x-mixed-replace": {}}}, 404: {}},
)
def stream_mjpeg(
    camera_id: str,
    user: User = Depends(require_teacher_stream),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    school_id = resolve_school_scope(db, user)
    if _camera_record(db, camera_id, school_id) is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} not found")
    if ingestion_service.get_worker(camera_id) is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} is not loaded")
    return StreamingResponse(
        _mjpeg_generator(camera_id),
        media_type=f"multipart/x-mixed-replace; boundary={_MJPEG_BOUNDARY}",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "Connection": "close",
        },
    )
