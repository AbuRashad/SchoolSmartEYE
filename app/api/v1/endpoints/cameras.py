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

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

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


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("", response_model=list[CameraInfo])
def list_cameras() -> list[CameraInfo]:
    """List all registered live cameras with current status."""
    out: list[CameraInfo] = []
    for src in ingestion_service.list_sources():
        info = _info_for(src.camera_id)
        if info is not None:
            out.append(info)
    return out


@router.post("", response_model=CameraInfo, status_code=status.HTTP_201_CREATED)
def register_camera(payload: CameraCreate) -> CameraInfo:
    """Register a new live camera and start streaming from it."""
    source = CameraSource(
        camera_id=payload.camera_id,
        zone_id=payload.zone_id,
        label=payload.label,
        source_url=payload.source_url,
        anonymize_faces=payload.anonymize_faces,
    )
    ingestion_service.register(source, autostart=True)
    info = _info_for(payload.camera_id)
    if info is None:  # pragma: no cover
        raise HTTPException(status_code=500, detail="Camera registration failed")
    return info


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def unregister_camera(camera_id: str) -> Response:
    if not ingestion_service.unregister(camera_id):
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{camera_id}/start", response_model=CameraInfo)
def start_camera(camera_id: str) -> CameraInfo:
    worker = ingestion_service.get_worker(camera_id)
    if worker is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} not found")
    worker.start()
    info = _info_for(camera_id)
    assert info is not None
    return info


@router.post("/{camera_id}/stop", response_model=CameraInfo)
def stop_camera(camera_id: str) -> CameraInfo:
    worker = ingestion_service.get_worker(camera_id)
    if worker is None:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id!r} not found")
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
def snapshot(camera_id: str) -> Response:
    """Return the latest JPEG frame from the camera (one-shot)."""
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
)
def stream_mjpeg(camera_id: str) -> StreamingResponse:
    """Live MJPEG multipart stream — drop straight into an `<img>` tag."""
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
