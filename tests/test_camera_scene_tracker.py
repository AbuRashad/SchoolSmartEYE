import pytest
from app.services.camera_event_intelligence import ObjectDetection
from app.services.camera_scene_tracker import SceneLocalIoUTracker, SceneTrackerConfig


def box(x1, y1, x2, y2, label="person"):
    return ObjectDetection(label, .9, x1, y1, x2, y2)


def test_associates_overlapping_detections_with_same_temporary_track():
    tracker = SceneLocalIoUTracker()
    first = tracker.update([box(0, 0, 20, 20)], now=1)[0]
    second = tracker.update([box(2, 0, 22, 20)], now=2)[0]
    assert first.track_id == second.track_id
    assert second.age_frames == 2


def test_new_track_for_non_overlapping_or_different_class():
    tracker = SceneLocalIoUTracker()
    first = tracker.update([box(0, 0, 10, 10)], now=1)[0]
    second = tracker.update([box(100, 100, 110, 110)], now=2)[0]
    assert first.track_id != second.track_id


def test_tracks_expire_after_configured_gap():
    tracker = SceneLocalIoUTracker(SceneTrackerConfig(max_missed_seconds=1))
    first = tracker.update([box(0, 0, 20, 20)], now=1)[0]
    second = tracker.update([box(0, 0, 20, 20)], now=3)[0]
    assert first.track_id != second.track_id


def test_reset_discards_session_tracks():
    tracker = SceneLocalIoUTracker()
    tracker.update([box(0, 0, 20, 20)], now=1)
    tracker.reset()
    assert tracker.active_track_count == 0


def test_track_capacity_is_bounded():
    tracker = SceneLocalIoUTracker(SceneTrackerConfig(max_tracks=1))
    results = tracker.update([box(0, 0, 10, 10), box(30, 30, 40, 40)], now=1)
    assert len(results) == 1
    assert tracker.active_track_count == 1


def test_rejects_invalid_config():
    with pytest.raises(ValueError):
        SceneTrackerConfig(iou_threshold=0)
