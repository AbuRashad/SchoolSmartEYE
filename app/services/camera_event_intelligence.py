"""Event-triggered camera scene analysis orchestration.

A reviewed local detector is injected at runtime. No model is downloaded and
no cloud inference or identity recognition is performed here. Findings are
candidates for authorized human review, never confirmed incidents.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from math import isfinite
from typing import Protocol, Sequence
from uuid import uuid4

import cv2
import numpy as np


class CameraEventType(str, Enum):
    PERSON_PRESENCE = "person_presence"
    CROWDING_CANDIDATE = "crowding_candidate"
    RESTRICTED_ZONE_ENTRY_CANDIDATE = "restricted_zone_entry_candidate"


@dataclass(frozen=True)
class ObjectDetection:
    label: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("detection label cannot be empty")
        coordinates = (self.x1, self.y1, self.x2, self.y2, self.confidence)
        if not all(isfinite(value) for value in coordinates):
            raise ValueError("confidence and bounding-box coordinates must be finite")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.x1 < 0 or self.y1 < 0 or self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("bounding box must have positive area and non-negative origin")


class ObjectDetector(Protocol):
    model_version: str

    def detect(self, frame: np.ndarray) -> Sequence[ObjectDetection]: ...


@dataclass(frozen=True)
class CameraFinding:
    finding_id: str
    event_type: CameraEventType
    confidence: float
    object_count: int
    evidence: dict[str, object]
    requires_human_review: bool = True
    status: str = "candidate"


@dataclass(frozen=True)
class CameraAnalysisSnapshot:
    event_id: str
    camera_id: str
    zone_id: str
    captured_at: str
    analyzed_at: str
    model_version: str
    frame_width: int
    frame_height: int
    findings: tuple[CameraFinding, ...]
    limitations: tuple[str, ...] = (
        "Automated findings are indicators, not confirmed incidents.",
        "No identity recognition or identity matching is performed.",
        "Results require authorized human review.",
    )

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["findings"] = [
            {**asdict(item), "event_type": item.event_type.value}
            for item in self.findings
        ]
        return result


@dataclass(frozen=True)
class CameraEventConfig:
    max_width: int = 640
    max_height: int = 360
    person_labels: tuple[str, ...] = ("person",)
    crowding_threshold: int = 5

    def __post_init__(self) -> None:
        if self.max_width < 1 or self.max_height < 1:
            raise ValueError("maximum frame dimensions must be positive")
        if self.crowding_threshold < 2:
            raise ValueError("crowding_threshold must be at least 2")
        if not self.person_labels or any(not label.strip() for label in self.person_labels):
            raise ValueError("person_labels must contain non-empty labels")


class CameraEventIntelligenceEngine:
    """Analyze one event-associated frame with an injected local detector."""

    def __init__(self, detector: ObjectDetector, config: CameraEventConfig | None = None) -> None:
        self.detector = detector
        self.config = config or CameraEventConfig()
        self._person_labels = {label.casefold() for label in self.config.person_labels}

    def analyze_frame(
        self, *, camera_id: str, zone_id: str, frame: np.ndarray,
        captured_at: datetime,
        restricted_zone_polygon: Sequence[tuple[float, float]] | None = None,
    ) -> CameraAnalysisSnapshot:
        if not camera_id.strip() or not zone_id.strip():
            raise ValueError("camera_id and zone_id are required")
        if captured_at.tzinfo is None or captured_at.utcoffset() is None:
            raise ValueError("captured_at must be timezone-aware")
        if not isinstance(frame, np.ndarray) or frame.size == 0 or frame.ndim != 3:
            raise ValueError("frame must be a non-empty color image")

        height, width = frame.shape[:2]
        prepared = self._resize_frame(frame)
        detections = tuple(self.detector.detect(prepared))
        people = [
            item for item in detections
            if item.label.casefold() in self._person_labels
            and item.x2 <= prepared.shape[1] and item.y2 <= prepared.shape[0]
        ]
        findings: list[CameraFinding] = []
        if people:
            findings.append(self._finding(
                CameraEventType.PERSON_PRESENCE, max(x.confidence for x in people), len(people),
                {"detector": "object_detection", "review_note": "Person presence candidate only."},
            ))
        if len(people) >= self.config.crowding_threshold:
            findings.append(self._finding(
                CameraEventType.CROWDING_CANDIDATE, max(x.confidence for x in people), len(people),
                {"threshold": self.config.crowding_threshold,
                 "review_note": "Count threshold is screening only, not a validated density measure."},
            ))
        if restricted_zone_polygon and people:
            hits = [x for x in people if self._center_inside_polygon(x, restricted_zone_polygon)]
            if hits:
                findings.append(self._finding(
                    CameraEventType.RESTRICTED_ZONE_ENTRY_CANDIDATE,
                    max(x.confidence for x in hits), len(hits),
                    {"zone_rule": "configured_polygon",
                     "review_note": "Polygon overlap is a candidate requiring human verification."},
                ))

        return CameraAnalysisSnapshot(
            event_id=str(uuid4()), camera_id=camera_id, zone_id=zone_id,
            captured_at=captured_at.astimezone(timezone.utc).isoformat(),
            analyzed_at=datetime.now(timezone.utc).isoformat(),
            model_version=str(self.detector.model_version), frame_width=width,
            frame_height=height, findings=tuple(findings),
        )

    def _resize_frame(self, frame: np.ndarray) -> np.ndarray:
        height, width = frame.shape[:2]
        scale = min(self.config.max_width / width, self.config.max_height / height, 1.0)
        if scale >= 1.0:
            return frame.copy()
        return cv2.resize(frame, (max(1, int(width * scale)), max(1, int(height * scale))),
                          interpolation=cv2.INTER_AREA)

    @staticmethod
    def _center_inside_polygon(detection: ObjectDetection,
                               polygon: Sequence[tuple[float, float]]) -> bool:
        if len(polygon) < 3:
            raise ValueError("restricted zone polygon must contain at least 3 points")
        center = (int((detection.x1 + detection.x2) / 2),
                  int((detection.y1 + detection.y2) / 2))
        contour = np.asarray(polygon, dtype=np.float32).reshape((-1, 1, 2))
        return cv2.pointPolygonTest(contour, center, False) >= 0

    @staticmethod
    def _finding(event_type: CameraEventType, confidence: float, object_count: int,
                 evidence: dict[str, object]) -> CameraFinding:
        return CameraFinding(str(uuid4()), event_type, round(float(confidence), 4),
                             object_count, evidence)
