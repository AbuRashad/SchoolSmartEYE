"""Camera health classification and deterministic synthetic scenarios.

This module consumes telemetry only. It never opens a camera, reads a frame,
or infers anything about people. Real telemetry can be connected later through
an authenticated edge-agent endpoint.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Iterator, Literal


class CameraHealthStatus(StrEnum):
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    STALLED = "stalled"


@dataclass(frozen=True, slots=True)
class CameraHealthMetrics:
    camera_id: str
    observed_at: datetime
    last_seen_age_seconds: float
    fps: float
    latency_ms: float
    consecutive_missed_heartbeats: int = 0
    reconnect_count: int = 0
    frozen_frame: bool = False

    def __post_init__(self) -> None:
        if not self.camera_id or len(self.camera_id) > 64:
            raise ValueError("camera_id must contain 1 to 64 characters")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        for name in ("last_seen_age_seconds", "fps", "latency_ms"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be finite and cannot be negative")
        if self.consecutive_missed_heartbeats < 0 or self.reconnect_count < 0:
            raise ValueError("heartbeat and reconnect counters cannot be negative")


@dataclass(frozen=True, slots=True)
class CameraHealthResult:
    camera_id: str
    status: CameraHealthStatus
    observed_at: datetime
    last_seen_age_seconds: float
    fps: float
    latency_ms: float
    consecutive_missed_heartbeats: int
    reconnect_count: int
    frozen_frame: bool


def classify_camera_health(
    metrics: CameraHealthMetrics,
    *,
    offline_after_seconds: float = 30.0,
    offline_after_missed_heartbeats: int = 3,
    degraded_below_fps: float = 5.0,
    degraded_above_latency_ms: float = 1000.0,
) -> CameraHealthResult:
    """Apply transparent thresholds; status is operational, not an AI inference."""
    if offline_after_seconds <= 0 or offline_after_missed_heartbeats < 1:
        raise ValueError("offline thresholds must be positive")
    if degraded_below_fps < 0 or degraded_above_latency_ms < 0:
        raise ValueError("degraded thresholds cannot be negative")

    if (
        metrics.last_seen_age_seconds >= offline_after_seconds
        or metrics.consecutive_missed_heartbeats >= offline_after_missed_heartbeats
    ):
        status = CameraHealthStatus.OFFLINE
    elif metrics.frozen_frame:
        status = CameraHealthStatus.STALLED
    elif (
        metrics.consecutive_missed_heartbeats > 0
        or metrics.fps < degraded_below_fps
        or metrics.latency_ms > degraded_above_latency_ms
    ):
        status = CameraHealthStatus.DEGRADED
    else:
        status = CameraHealthStatus.ONLINE

    return CameraHealthResult(
        camera_id=metrics.camera_id,
        status=status,
        observed_at=metrics.observed_at.astimezone(timezone.utc),
        last_seen_age_seconds=metrics.last_seen_age_seconds,
        fps=metrics.fps,
        latency_ms=metrics.latency_ms,
        consecutive_missed_heartbeats=metrics.consecutive_missed_heartbeats,
        reconnect_count=metrics.reconnect_count,
        frozen_frame=metrics.frozen_frame,
    )


HealthScenario = Literal["online", "degraded", "offline", "stalled", "reconnecting"]


def simulate_camera_health(
    camera_id: str,
    scenario: HealthScenario,
    *,
    start_at: datetime,
    samples: int = 6,
    interval_seconds: int = 5,
) -> Iterator[CameraHealthResult]:
    """Yield repeatable synthetic telemetry for tests and offline demonstrations."""
    if start_at.tzinfo is None or start_at.utcoffset() is None:
        raise ValueError("start_at must be timezone-aware")
    if not 1 <= samples <= 1000:
        raise ValueError("samples must be between 1 and 1000")
    if interval_seconds < 1:
        raise ValueError("interval_seconds must be positive")

    for index in range(samples):
        age = 1.0
        fps, latency, missed, reconnects, frozen = 24.0, 80.0, 0, 0, False
        if scenario == "degraded":
            fps, latency, missed = 3.0, 1450.0, 1
        elif scenario == "offline":
            age, fps, latency, missed = 60.0 + index * interval_seconds, 0.0, 0.0, 3 + index
        elif scenario == "stalled":
            fps, frozen = 0.0, True
        elif scenario == "reconnecting":
            if index < samples - 1:
                age, fps, missed = 35.0, 0.0, 3
            else:
                reconnects, fps = 1, 18.0
        elif scenario != "online":
            raise ValueError(f"unsupported health scenario: {scenario}")

        metrics = CameraHealthMetrics(
            camera_id=camera_id,
            observed_at=start_at + timedelta(seconds=index * interval_seconds),
            last_seen_age_seconds=age,
            fps=fps,
            latency_ms=latency,
            consecutive_missed_heartbeats=missed,
            reconnect_count=reconnects,
            frozen_frame=frozen,
        )
        yield classify_camera_health(metrics)
