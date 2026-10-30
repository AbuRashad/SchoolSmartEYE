from datetime import datetime, timezone

import numpy as np
import pytest

from app.services.camera_event_intelligence import (
    CameraEventConfig, CameraEventIntelligenceEngine, CameraEventType, ObjectDetection,
)


class FakeDetector:
    model_version = "fake-test-detector-1"

    def __init__(self, detections):
        self.detections = detections
        self.last_shape = None

    def detect(self, frame):
        self.last_shape = frame.shape
        return self.detections


def detection(x1=10, y1=10, x2=40, y2=60, confidence=0.9, label="person"):
    return ObjectDetection(label, confidence, x1, y1, x2, y2)


def analyze(detector, **kwargs):
    engine = CameraEventIntelligenceEngine(detector)
    return engine.analyze_frame(
        camera_id="cam-test", zone_id="zone-test",
        frame=np.zeros((720, 1280, 3), dtype=np.uint8),
        captured_at=datetime(2026, 10, 30, tzinfo=timezone.utc), **kwargs,
    )


def test_person_presence_is_candidate_and_requires_human_review():
    snapshot = analyze(FakeDetector([detection()]))
    assert len(snapshot.findings) == 1
    finding = snapshot.findings[0]
    assert finding.event_type is CameraEventType.PERSON_PRESENCE
    assert finding.status == "candidate"
    assert finding.requires_human_review is True
    assert snapshot.model_version == "fake-test-detector-1"


def test_crowding_candidate_uses_configurable_count_threshold():
    detector = FakeDetector([detection(x1=i * 50, x2=i * 50 + 20) for i in range(5)])
    engine = CameraEventIntelligenceEngine(detector, CameraEventConfig(crowding_threshold=5))
    snapshot = engine.analyze_frame(
        camera_id="cam", zone_id="zone", frame=np.zeros((400, 400, 3), dtype=np.uint8),
        captured_at=datetime.now(timezone.utc),
    )
    assert [x.event_type for x in snapshot.findings] == [
        CameraEventType.PERSON_PRESENCE, CameraEventType.CROWDING_CANDIDATE,
    ]
    assert snapshot.findings[1].object_count == 5


def test_restricted_zone_candidate_uses_configured_polygon():
    snapshot = analyze(FakeDetector([detection()]), restricted_zone_polygon=[
        (0, 0), (100, 0), (100, 100), (0, 100),
    ])
    assert any(x.event_type is CameraEventType.RESTRICTED_ZONE_ENTRY_CANDIDATE
               for x in snapshot.findings)


def test_non_person_objects_are_ignored():
    assert analyze(FakeDetector([detection(label="car")])).findings == ()


def test_detector_receives_downscaled_frame():
    detector = FakeDetector([])
    analyze(detector)
    assert detector.last_shape == (360, 640, 3)


def test_snapshot_serialization_is_json_friendly_and_has_no_identity_fields():
    data = analyze(FakeDetector([detection()])).to_dict()
    assert data["findings"][0]["event_type"] == "person_presence"
    assert data["findings"][0]["requires_human_review"] is True
    assert "identity" not in str(data).lower()


def test_naive_timestamp_is_rejected():
    engine = CameraEventIntelligenceEngine(FakeDetector([]))
    with pytest.raises(ValueError):
        engine.analyze_frame(camera_id="cam", zone_id="zone",
            frame=np.zeros((20, 20, 3), dtype=np.uint8), captured_at=datetime(2026, 10, 30))


def test_invalid_frame_is_rejected():
    engine = CameraEventIntelligenceEngine(FakeDetector([]))
    with pytest.raises(ValueError):
        engine.analyze_frame(camera_id="cam", zone_id="zone", frame=np.array([]),
                             captured_at=datetime.now(timezone.utc))


def test_detection_rejects_invalid_confidence_and_box():
    with pytest.raises(ValueError):
        ObjectDetection("person", 1.5, 0, 0, 10, 10)
    with pytest.raises(ValueError):
        ObjectDetection("person", 0.8, 10, 10, 10, 20)


def test_invalid_restricted_polygon_is_rejected():
    with pytest.raises(ValueError):
        analyze(FakeDetector([detection()]), restricted_zone_polygon=[(0, 0), (10, 10)])
