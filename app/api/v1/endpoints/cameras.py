"""Live camera REST + MJPEG streaming endpoints.

Endpoints:
    GET    /api/v1/cameras                          → list registered live cameras
    POST   /api/v1/cameras                          → register a new camera (and start)
    DELETE /api/v1/cameras/{camera_id}              → unregister & stop
    POST   /api/v1/cameras/{camera_id}/start        → restart worker
    POST   /api/v1/cameras/{camera_id}/stop         → stop worker (keep registration)
    GET    /api/v1/cameras/{camera_id}/snapshot.jpg → latest JPEG (one-shot)
    GET    /api/v1/cameras/{camera_id}/stream.mjpg  → live MJPEG multipart stream
"""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import require_principal, require_teacher, require_teacher_stream, role_of
from app.core.governance_layer import SCOPE_LEVEL, Role
from app.db.models import User
from app.services.camera_ingestion import CameraSource, ingestion_service
from app.units.unit_01.module import StreamStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cameras", tags=["cameras"])

_MJPEG_BOUNDARY = "frame"


# ── Schemas ───────────────────────────────────────────────────────────────────


class CameraCreate(BaseModel):
    camera_id: str = Field(..., min_length=1, max_length=64, description="Unique short id, e.g. 'cam-gate'")
    zone_id: str = Field(..., min_length=1, description="Zone id from /api/v1/dashboard/live (e.g. 'zone-main-gate')")
    label: str = Field(..., min_length=1, description="Human-readable name shown in the UI")
    source_url: str = Field(..., min_length=1, description="RTSP/HTTP URL, USB index ('0'), or file path")
    anonymize_faces: bool = Field(default=True, description="Apply Unit 14 face anonymization to every frame")


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


# ── Helpers ───────────────────────────────────────────────────────────────────


def _info_for(camera_id: str, school_id: str) -> CameraInfo | None:
    worker = ingestion_service.get_worker(camera_id)
    source = next((s for s in ingestion_service.list_sources() if s.camera_id == camera_id), None)
    stream = ingestion_service.capture_unit.get_stream(camera_id)
    if worker is None or source is None or stream is None or source.school_id != school_id:
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


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("", response_model=list[CameraInfo])
def list_cameras(user: User = Depends(require_teacher)) -> list[CameraInfo]:
    """List all registered live cameras with current status.

    `source_url` may embed credentials, so it is only revealed to principal+.
    """
    if not user.school_id:
        raise HTTPException(status_code=403, detail="User is not assigned to a school")
    role = role_of(user)
    can_see_source = role is not None and SCOPE_LEVEL[role] >= SCOPE_LEVEL[Role.PRINCIPAL]
    out: list[CameraInfo] = []
    for src in ingestion_service.list_sources():
        if src.school_id != user.school_id:
            continue
        info = _info_for(src.camera_id, user.school_id)
        if info is not None:
            out.append(info if can_see_source else info.model_copy(update={"source_url": "hidden"}))
    return out


@router.post(
    "",
    response_model=CameraInfo,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_principal)],
)
def register_camera(payload: CameraCreate, user: User = Depends(require_principal)) -> CameraInfo:
    """Register a new live camera and start streaming from it."""
    if not user.school_id:
        raise HTTPException(status_code=403, detail="User is not assigned to a school")
    if any(src.camera_id == payload.camera_id for src in ingestion_service.list_sources()):
        raise HTTPException(status_code=409, detail="Camera ID is already registered")
    source = CameraSource(
        camera_id=payload.camera_id,
        zone_id=payload.zone_id,
        label=payload.label,
        source_url=payload.source_url,
        anonymize_faces=payload.anonymize_faces,
        school_id=user.school_id,
    )
    ingestion_service.register(source, autostart=True)
    info = _info_for(payload.camera_id, user.school_id)
    if info is None:  # pragma: no cover
        raise HTTPException(status_code=500, detail="Camera registration failed")
    return info


@router.delete(
    "/{camera_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_principal)],
)
def unregister_camera(camera_id: str, user: User = Depends(require_principal)) -> Response:
    if not user.school_id:
        raise HTTPException(status_code=403, detail="User is not assigned to a school")
    source = next((s for s in ingestion_service.list_sources() if s.camera_id == camera_id), None)
    if source is None or source.school_id != user.school_id:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} not found")
    if not ingestion_service.unregister(camera_id):
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{camera_id}/start", response_model=CameraInfo, dependencies=[Depends(require_principal)]
)
def start_camera(camera_id: str, user: User = Depends(require_principal)) -> CameraInfo:
    if not user.school_id:
        raise HTTPException(status_code=403, detail="User is not assigned to a school")
    info = _info_for(camera_id, user.school_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} not found")
    worker = ingestion_service.get_worker(camera_id)
    if worker is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} not found")
    worker.start()
    info = _info_for(camera_id, user.school_id)
    assert info is not None
    return info


@router.post(
    "/{camera_id}/stop", response_model=CameraInfo, dependencies=[Depends(require_principal)]
)
def stop_camera(camera_id: str, user: User = Depends(require_principal)) -> CameraInfo:
    if not user.school_id:
        raise HTTPException(status_code=403, detail="User is not assigned to a school")
    info = _info_for(camera_id, user.school_id)
    if info is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} not found")
    worker = ingestion_service.get_worker(camera_id)
    if worker is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} not found")
    worker.stop()
    stream = ingestion_service.capture_unit.get_stream(camera_id)
    if stream is not None:
        stream.status = StreamStatus.OFFLINE
    info = _info_for(camera_id, user.school_id)
    assert info is not None
    return info


@router.get(
    "/{camera_id}/snapshot.jpg",
    responses={200: {"content": {"image/jpeg": {}}}, 404: {}, 503: {}},
    dependencies=[Depends(require_teacher_stream)],
)
def snapshot(camera_id: str, user: User = Depends(require_teacher_stream)) -> Response:
    """Return the latest JPEG frame from a camera owned by the authenticated school."""
    if not user.school_id or _info_for(camera_id, user.school_id) is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} not found")
    worker = ingestion_service.get_worker(camera_id)
    if worker is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} not found")
    jpeg = worker.get_latest_jpeg()
    if jpeg is None:
        raise HTTPException(
            status_code=503,
            detail=f"No frame available yet for {camera_id!r} — camera may still be connecting.",
        )
    return Response(
        content=jpeg,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate", "Pragma": "no-cache"},
    )


async def _mjpeg_generator(camera_id: str) -> AsyncIterator[bytes]:
    """Async generator producing multipart/x-mixed-replace MJPEG frames."""
    boundary = f"--{_MJPEG_BOUNDARY}\r\n".encode("ascii")
    worker = ingestion_service.get_worker(camera_id)
    if worker is None:
        return

    last_frame_id = id(None)
    while True:
        # Run the blocking wait in a thread so we don't stall the event loop
        jpeg = await asyncio.to_thread(worker.wait_next_frame, 5.0)
        if jpeg is None or id(jpeg) == last_frame_id:
            # heartbeat / wait for new frame
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
    dependencies=[Depends(require_teacher_stream)],
)
def stream_mjpeg(camera_id: str, user: User = Depends(require_teacher_stream)) -> StreamingResponse:
    """Live MJPEG multipart stream for a camera owned by the authenticated school."""
    if not user.school_id or _info_for(camera_id, user.school_id) is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} not found")
    worker = ingestion_service.get_worker(camera_id)
    if worker is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} not found")
    return StreamingResponse(
        _mjpeg_generator(camera_id),
        media_type=f"multipart/x-mixed-replace; boundary={_MJPEG_BOUNDARY}",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
            "Connection": "close",
        },
    )
