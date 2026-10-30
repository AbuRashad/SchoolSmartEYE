"""Short-lived scene-local detection association (not identity tracking).

This lightweight IoU tracker associates detections across adjacent sampled frames.
Track IDs are random, camera-session scoped, expire quickly, and must never be
used to identify a person across cameras or sessions.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from time import monotonic
from uuid import uuid4
from typing import Sequence

from app.services.camera_event_intelligence import ObjectDetection


@dataclass(frozen=True)
class TrackedDetection:
    track_id: str
    detection: ObjectDetection
    age_frames: int
    missed_frames: int


@dataclass
class _Track:
    track_id: str
    detection: ObjectDetection
    last_seen: float
    age_frames: int = 1
    missed_frames: int = 0


@dataclass(frozen=True)
class SceneTrackerConfig:
    iou_threshold: float = 0.30
    max_missed_seconds: float = 2.0
    max_tracks: int = 64

    def __post_init__(self):
        if not isfinite(self.iou_threshold) or not 0 < self.iou_threshold <= 1:
            raise ValueError("iou_threshold must be in (0, 1]")
        if not isfinite(self.max_missed_seconds) or self.max_missed_seconds <= 0:
            raise ValueError("max_missed_seconds must be positive")
        if self.max_tracks < 1:
            raise ValueError("max_tracks must be positive")


class SceneLocalIoUTracker:
    """Greedy IoU association for one camera session; no appearance features."""

    def __init__(self, config: SceneTrackerConfig | None = None, clock=monotonic):
        self.config = config or SceneTrackerConfig()
        self._clock = clock
        self._tracks: dict[str, _Track] = {}

    @staticmethod
    def _iou(a: ObjectDetection, b: ObjectDetection) -> float:
        x1, y1 = max(a.x1, b.x1), max(a.y1, b.y1)
        x2, y2 = min(a.x2, b.x2), min(a.y2, b.y2)
        intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
        area_a = (a.x2 - a.x1) * (a.y2 - a.y1)
        area_b = (b.x2 - b.x1) * (b.y2 - b.y1)
        union = area_a + area_b - intersection
        return intersection / union if union > 0 else 0.0

    def update(self, detections: Sequence[ObjectDetection], now: float | None = None) -> tuple[TrackedDetection, ...]:
        current = self._clock() if now is None else float(now)
        if not isfinite(current):
            raise ValueError("now must be finite")
        for track_id in list(self._tracks):
            if current - self._tracks[track_id].last_seen > self.config.max_missed_seconds:
                del self._tracks[track_id]

        candidates = []
        for track_id, track in self._tracks.items():
            for index, detection in enumerate(detections):
                if track.detection.label.casefold() != detection.label.casefold():
                    continue
                score = self._iou(track.detection, detection)
                if score >= self.config.iou_threshold:
                    candidates.append((score, track_id, index))
        candidates.sort(reverse=True)
        matched_tracks, matched_detections = set(), set()
        assignments: dict[int, str] = {}
        for _, track_id, index in candidates:
            if track_id in matched_tracks or index in matched_detections:
                continue
            matched_tracks.add(track_id)
            matched_detections.add(index)
            assignments[index] = track_id

        for track_id, track in self._tracks.items():
            if track_id not in matched_tracks:
                track.missed_frames += 1

        for index, detection in enumerate(detections):
            if index in assignments:
                track = self._tracks[assignments[index]]
                track.detection = detection
                track.last_seen = current
                track.age_frames += 1
                track.missed_frames = 0
            elif len(self._tracks) < self.config.max_tracks:
                track_id = uuid4().hex
                self._tracks[track_id] = _Track(track_id, detection, current)
                assignments[index] = track_id

        return tuple(
            TrackedDetection(assignments[index], detection,
                self._tracks[assignments[index]].age_frames,
                self._tracks[assignments[index]].missed_frames)
            for index, detection in enumerate(detections) if index in assignments
        )

    def reset(self) -> None:
        """End this camera session and discard every temporary track."""
        self._tracks.clear()

    @property
    def active_track_count(self) -> int:
        return len(self._tracks)
