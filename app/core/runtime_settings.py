"""Runtime-tunable settings singleton.

Exposes a small set of knobs that operators need to adjust without restarting
the process (e.g. bumping camera FPS during an event, or lowering JPEG quality
when the network gets congested). Values are seeded from `app.core.config.settings`
on first access and can be mutated at runtime by the `PATCH /api/v1/settings`
endpoint. All consumers should read from this module (not directly from
`config.settings`) when they want live values.
"""
from __future__ import annotations

import threading
from dataclasses import asdict, dataclass

from app.core.config import settings


@dataclass
class RuntimeSettings:
    """Mutable operational knobs. All values have safe defaults from `config.settings`."""
    # Camera ingestion
    camera_max_fps: float
    camera_jpeg_quality: int
    camera_reconnect_seconds: float
    camera_anonymize_faces: bool

    # Dashboard / SSI
    ssi_benchmark: float

    # Data governance
    video_ttl_hours: int

    # Bracelet thresholds
    bracelet_low_battery_percent: int


_lock = threading.Lock()

_runtime = RuntimeSettings(
    camera_max_fps=float(settings.camera_max_fps),
    camera_jpeg_quality=int(settings.camera_jpeg_quality),
    camera_reconnect_seconds=float(settings.camera_reconnect_seconds),
    camera_anonymize_faces=bool(settings.camera_anonymize_faces),
    ssi_benchmark=75.0,
    video_ttl_hours=int(settings.video_ttl_hours),
    bracelet_low_battery_percent=20,
)


def get_runtime_settings() -> RuntimeSettings:
    """Return the current runtime settings snapshot."""
    with _lock:
        return RuntimeSettings(**asdict(_runtime))


def update_runtime_settings(**updates: object) -> RuntimeSettings:
    """Apply partial updates to the runtime settings.

    Unknown keys are ignored. Values are lightly validated and clamped.
    Returns the new snapshot.
    """
    global _runtime
    with _lock:
        data = asdict(_runtime)
        for key, value in updates.items():
            if key not in data or value is None:
                continue

            if key == "camera_max_fps":
                data[key] = max(0.5, min(60.0, float(value)))
            elif key == "camera_jpeg_quality":
                data[key] = max(10, min(100, int(value)))
            elif key == "camera_reconnect_seconds":
                data[key] = max(0.5, min(120.0, float(value)))
            elif key == "camera_anonymize_faces":
                data[key] = bool(value)
            elif key == "ssi_benchmark":
                data[key] = max(0.0, min(100.0, float(value)))
            elif key == "video_ttl_hours":
                data[key] = max(1, min(720, int(value)))
            elif key == "bracelet_low_battery_percent":
                data[key] = max(1, min(99, int(value)))

        _runtime = RuntimeSettings(**data)
        return RuntimeSettings(**asdict(_runtime))


def as_dict() -> dict[str, object]:
    """Serialize the current runtime settings to a plain dict."""
    return asdict(get_runtime_settings())
