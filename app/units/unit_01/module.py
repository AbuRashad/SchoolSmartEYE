"""Unit 01: Video Capture Unit — استلام البث من الكاميرات في المواقع الحيوية."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

UNIT_01_NAME = "Video Capture Unit"


class StreamStatus(str, Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    OFFLINE = "offline"


@dataclass
class CameraStream:
    camera_id: str
    location_id: str
    zone_label: str
    resolution: tuple[int, int] = (1280, 720)
    fps: int = 25
    status: StreamStatus = StreamStatus.ACTIVE
    last_frame_at: datetime | None = None
    total_frames_captured: int = 0
    drop_count: int = 0
    source_url: str | None = None
    last_error: str | None = None

    @property
    def drop_rate(self) -> float:
        total = self.total_frames_captured + self.drop_count
        if total == 0:
            return 0.0
        return self.drop_count / total

    def mark_frame_received(self, at: datetime | None = None) -> None:
        self.last_frame_at = at or datetime.now(timezone.utc).replace(tzinfo=None)
        self.total_frames_captured += 1
        self.last_error = None
        # any successful frame promotes us back to ACTIVE
        self.status = StreamStatus.ACTIVE

    def mark_frame_dropped(self) -> None:
        self.drop_count += 1
        if self.drop_rate > 0.3:
            self.status = StreamStatus.DEGRADED

    def mark_disconnected(self, error: str | None = None) -> None:
        """Mark the stream as offline (e.g. RTSP connection lost)."""
        self.status = StreamStatus.OFFLINE
        if error is not None:
            self.last_error = error

    def to_dict(self) -> dict[str, object]:
        return {
            "camera_id": self.camera_id,
            "location_id": self.location_id,
            "zone_label": self.zone_label,
            "resolution": list(self.resolution),
            "fps": self.fps,
            "status": self.status.value,
            "last_frame_at": self.last_frame_at.isoformat() if self.last_frame_at else None,
            "total_frames_captured": self.total_frames_captured,
            "drop_rate": round(self.drop_rate, 4),
            "source_url": self.source_url,
            "last_error": self.last_error,
        }


class VideoCaptureUnit:
    """Manages live camera streams across all school zones."""

    def __init__(self) -> None:
        self._streams: dict[str, CameraStream] = {}

    def register_stream(
        self,
        camera_id: str,
        location_id: str,
        zone_label: str,
        resolution: tuple[int, int] = (1280, 720),
        fps: int = 25,
        source_url: str | None = None,
    ) -> CameraStream:
        stream = CameraStream(
            camera_id=camera_id,
            location_id=location_id,
            zone_label=zone_label,
            resolution=resolution,
            fps=fps,
            source_url=source_url,
        )
        self._streams[camera_id] = stream
        return stream

    def unregister_stream(self, camera_id: str) -> bool:
        return self._streams.pop(camera_id, None) is not None

    def get_stream(self, camera_id: str) -> CameraStream | None:
        return self._streams.get(camera_id)

    def all_streams(self) -> list[CameraStream]:
        return list(self._streams.values())

    def active_streams(self) -> list[CameraStream]:
        return [s for s in self._streams.values() if s.status != StreamStatus.OFFLINE]

    def health_summary(self) -> dict[str, object]:
        streams = self.all_streams()
        active = sum(1 for s in streams if s.status == StreamStatus.ACTIVE)
        degraded = sum(1 for s in streams if s.status == StreamStatus.DEGRADED)
        offline = sum(1 for s in streams if s.status == StreamStatus.OFFLINE)
        return {
            "total": len(streams),
            "active": active,
            "degraded": degraded,
            "offline": offline,
            "streams": [s.to_dict() for s in streams],
        }
