from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from app.services.camera_event_intelligence import (
    CameraEventIntelligenceEngine,
    ObjectDetection,
)
from app.services.camera_event_pipeline import CameraEventPipeline, EventFrame


class FakeDetector:
    model_version = "test-fake-v1"

    def __init__(self):
        self.calls = 0

    def detect(self, frame):
        self.calls += 1
        return [ObjectDetection("person", 0.91, 5, 5, 20, 30)]


def make_frames(count=2):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [
        EventFrame(np.zeros((48, 64, 3), dtype=np.uint8), start + timedelta(seconds=i))
        for i in range(count)
    ]


def test_pipeline_analyzes_only_supplied_event_frames_in_order():
    detector = FakeDetector()
    pipeline = CameraEventPipeline(CameraEventIntelligenceEngine(detector))
    batch = pipeline.analyze_event(
        event_id="evt-1", camera_id="cam-1", zone_id="gate",
        frames=make_frames(3),
    )

    assert batch.event_id == "evt-1"
    assert batch.frame_count == 3
    assert batch.finding_count == 3
    assert detector.calls == 3
    assert batch.requires_human_review is True
    assert batch.status == "candidate"
    assert all(snapshot.camera_id == "cam-1" for snapshot in batch.snapshots)


def test_pipeline_serialization_contains_no_frame_pixels_or_track_ids():
    pipeline = CameraEventPipeline(CameraEventIntelligenceEngine(FakeDetector()))
    payload = pipeline.analyze_event(
        event_id="evt-2", camera_id="cam-1", zone_id="hall", frames=make_frames(1)
    ).to_dict()

    assert "frame" not in payload
    assert "track_id" not in str(payload)
    assert payload["snapshots"][0]["findings"][0]["requires_human_review"] is True


def test_pipeline_rejects_empty_event_and_too_many_frames():
    pipeline = CameraEventPipeline(CameraEventIntelligenceEngine(FakeDetector()), max_frames_per_event=1)
    with pytest.raises(ValueError, match="at least one"):
        pipeline.analyze_event(event_id="e", camera_id="c", zone_id="z", frames=[])
    with pytest.raises(ValueError, match="max_frames"):
        pipeline.analyze_event(event_id="e", camera_id="c", zone_id="z", frames=make_frames(2))


def test_pipeline_rejects_non_monotonic_or_naive_timestamps():
    pipeline = CameraEventPipeline(CameraEventIntelligenceEngine(FakeDetector()))
    frames = make_frames(2)
    frames[1] = EventFrame(frames[1].frame, frames[0].captured_at)
    with pytest.raises(ValueError, match="strictly increasing"):
        pipeline.analyze_event(event_id="e", camera_id="c", zone_id="z", frames=frames)

    naive = EventFrame(np.zeros((10, 10, 3), dtype=np.uint8), datetime(2026, 1, 1))
    with pytest.raises(ValueError, match="timezone-aware"):
        pipeline.analyze_event(event_id="e", camera_id="c", zone_id="z", frames=[naive])


def test_pipeline_rejects_missing_identifiers_and_invalid_frame_item():
    pipeline = CameraEventPipeline(CameraEventIntelligenceEngine(FakeDetector()))
    with pytest.raises(ValueError, match="required"):
        pipeline.analyze_event(event_id="", camera_id="c", zone_id="z", frames=make_frames(1))
    with pytest.raises(TypeError, match="EventFrame"):
        pipeline.analyze_event(event_id="e", camera_id="c", zone_id="z", frames=[object()])


def test_pipeline_rejects_invalid_max_frames():
    with pytest.raises(ValueError, match="positive"):
        CameraEventPipeline(CameraEventIntelligenceEngine(FakeDetector()), max_frames_per_event=0)
