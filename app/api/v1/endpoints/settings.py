"""Runtime settings GET / PATCH endpoint used by the Control Panel."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.runtime_settings import (
    RuntimeSettings,
    get_runtime_settings,
    update_runtime_settings,
)

router = APIRouter(prefix="/settings", tags=["control"])


class SettingsOut(BaseModel):
    camera_max_fps: float
    camera_jpeg_quality: int
    camera_reconnect_seconds: float
    camera_anonymize_faces: bool
    ssi_benchmark: float
    video_ttl_hours: int
    bracelet_low_battery_percent: int


class SettingsUpdate(BaseModel):
    camera_max_fps: float | None = Field(default=None, ge=0.5, le=60.0)
    camera_jpeg_quality: int | None = Field(default=None, ge=10, le=100)
    camera_reconnect_seconds: float | None = Field(default=None, ge=0.5, le=120.0)
    camera_anonymize_faces: bool | None = None
    ssi_benchmark: float | None = Field(default=None, ge=0.0, le=100.0)
    video_ttl_hours: int | None = Field(default=None, ge=1, le=720)
    bracelet_low_battery_percent: int | None = Field(default=None, ge=1, le=99)


def _to_out(rt: RuntimeSettings) -> SettingsOut:
    return SettingsOut(
        camera_max_fps=rt.camera_max_fps,
        camera_jpeg_quality=rt.camera_jpeg_quality,
        camera_reconnect_seconds=rt.camera_reconnect_seconds,
        camera_anonymize_faces=rt.camera_anonymize_faces,
        ssi_benchmark=rt.ssi_benchmark,
        video_ttl_hours=rt.video_ttl_hours,
        bracelet_low_battery_percent=rt.bracelet_low_battery_percent,
    )


@router.get("", response_model=SettingsOut)
def read_settings() -> SettingsOut:
    return _to_out(get_runtime_settings())


@router.patch("", response_model=SettingsOut)
def patch_settings(payload: SettingsUpdate) -> SettingsOut:
    updated = update_runtime_settings(**payload.model_dump(exclude_none=True))
    return _to_out(updated)
