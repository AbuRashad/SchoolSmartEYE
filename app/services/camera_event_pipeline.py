"""Bounded, in-memory orchestration for event-associated camera frames.

This pipeline accepts frames only after an upstream event trigger. It does not
open streams, persist frames, create alerts, or perform identity recognition.
Every finding remains a candidate for authorized human review.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Iterable, Sequence

import numpy as np

from app.services.camera_event_intelligence import (
    CameraAnalysisSnapshot,
    CameraEventIntelligenceEngine,
)


@dataclass(frozen=True)
class EventFrame:
    frame: np.ndarray
    captured_at: datetime


@dataclass(frozen=True)
class CameraEventBatch:
    event_id: str
    camera_id: str
    zone_id: str
    frame_count: int
    snapshots: tuple[CameraAnalysisSnapshot, ...]
    requires_human_review: bool = True
    status: str = "candidate"

    @property
    def finding_count(self) -> int:
        return sum(len(snapshot.findings) for snapshot in self.snapshots)

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "camera_id": self.camera_id,
            "zone_id": self.zone_id,
            "frame_count": self.frame_count,
            "finding_count": self.finding_count,
            "snapshots": [snapshot.to_dict() for snapshot in self.snapshots],
            "requires_human_review": self.requires_human_review,
            "status": self.status,
        }


class CameraEventPipeline:
    """Analyze a bounded clip supplied by an event trigger, in memory only."""

    def __init__(
        self,
        engine: CameraEventIntelligenceEngine,
        *,
        max_frames_per_event: int = 12,
    ) -> None:
        if max_frames_per_event < 1:
            raise ValueError("max_frames_per_event must be positive")
        self.engine = engine
        self.max_frames_per_event = max_frames_per_event

    def analyze_event(
        self,
        *,
        event_id: str,
        camera_id: str,
        zone_id: str,
        frames: Iterable[EventFrame],
        restricted_zone_polygon: Sequence[tuple[float, float]] | None = None,
    ) -> CameraEventBatch:
        if not event_id.strip() or not camera_id.strip() or not zone_id.strip():
            raise ValueError("event_id, camera_id, and zone_id are required")

        snapshots: list[CameraAnalysisSnapshot] = []
        previous_time: datetime | None = None
        for index, item in enumerate(frames):
            if index >= self.max_frames_per_event:
                raise ValueError("event exceeds max_frames_per_event")
            if not isinstance(item, EventFrame):
                raise TypeError("frames must contain EventFrame values")
            if item.captured_at.tzinfo is None or item.captured_at.utcoffset() is None:
                raise ValueError("frame timestamps must be timezone-aware")
            if previous_time is not None and item.captured_at <= previous_time:
                raise ValueError("frame timestamps must be strictly increasing")
            previous_time = item.captured_at
            snapshot = self.engine.analyze_frame(
                camera_id=camera_id,
                zone_id=zone_id,
                frame=item.frame,
                captured_at=item.captured_at,
                restricted_zone_polygon=restricted_zone_polygon,
            )
            snapshots.append(replace(snapshot, event_id=event_id))

        if not snapshots:
            raise ValueError("at least one event frame is required")

        return CameraEventBatch(
            event_id=event_id,
            camera_id=camera_id,
            zone_id=zone_id,
            frame_count=len(snapshots),
            snapshots=tuple(snapshots),
        )
