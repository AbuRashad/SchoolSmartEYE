import pytest

from app.services.camera_cv_runtime import (
    CameraCVConfig,
    FrameSamplingGate,
    LatestFrameQueue,
)


def test_camera_cv_config_has_bounded_cpu_defaults():
    config = CameraCVConfig()
    assert config.sample_interval_seconds == 1.0
    assert config.max_width == 640
    assert config.max_height == 360
    assert config.max_pending_frames == 2
    assert config.max_concurrent_inference_jobs == 1


@pytest.mark.parametrize("kwargs", [
    {"sample_interval_seconds": 0},
    {"max_width": 0},
    {"max_height": 0},
    {"max_pending_frames": 0},
    {"max_concurrent_inference_jobs": 0},
])
def test_camera_cv_config_rejects_invalid_limits(kwargs):
    with pytest.raises(ValueError):
        CameraCVConfig(**kwargs)


def test_frame_sampling_gate_uses_monotonic_intervals():
    gate = FrameSamplingGate(1.0, clock=lambda: 10.0)
    assert gate.should_accept(now=10.0)
    assert not gate.should_accept(now=10.5)
    assert gate.should_accept(now=11.0)


def test_frame_sampling_gate_reset_allows_immediate_frame():
    gate = FrameSamplingGate(5.0, clock=lambda: 10.0)
    assert gate.should_accept(now=10.0)
    assert not gate.should_accept(now=11.0)
    gate.reset()
    assert gate.should_accept(now=11.0)


def test_latest_frame_queue_drops_oldest_when_full():
    frames = LatestFrameQueue[str](maxsize=2)
    frames.put_latest("frame-1")
    frames.put_latest("frame-2")
    frames.put_latest("frame-3")

    assert frames.pending_count == 2
    assert frames.dropped_count == 1
    assert frames.get_nowait() == "frame-2"
    assert frames.get_nowait() == "frame-3"


def test_latest_frame_queue_preserves_latest_frame_under_repeated_overload():
    frames = LatestFrameQueue[int](maxsize=1)
    for value in range(100):
        frames.put_latest(value)

    assert frames.pending_count == 1
    assert frames.dropped_count == 99
    assert frames.get_nowait() == 99
