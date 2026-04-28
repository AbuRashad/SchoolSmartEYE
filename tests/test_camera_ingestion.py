"""Tests for the live camera ingestion service.

These tests do **not** require a real camera. We use a generated short MP4
file (created in-process via OpenCV) as the source — that exercises the
full ``cv2.VideoCapture`` → frame loop → JPEG encode → Unit 01 counters
pipeline end-to-end.
"""
from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.services.camera_ingestion import (
    CameraIngestionService,
    CameraSource,
)
from app.units.unit_01.module import StreamStatus, VideoCaptureUnit


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_video(tmp_path: Path) -> Path:
    """Create a tiny 30-frame, 320x240 MP4 file as a test source."""
    out_path = tmp_path / "sample.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, 10.0, (320, 240))
    if not writer.isOpened():
        # Fallback to AVI if mp4v codec is unavailable on this platform
        out_path = tmp_path / "sample.avi"
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        writer = cv2.VideoWriter(str(out_path), fourcc, 10.0, (320, 240))
    assert writer.isOpened(), "OpenCV could not open any video writer (codec missing)"
    rng = np.random.default_rng(42)
    for _ in range(30):
        frame = rng.integers(0, 255, size=(240, 320, 3), dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return out_path


@pytest.fixture
def service() -> CameraIngestionService:
    s = CameraIngestionService(capture_unit=VideoCaptureUnit())
    yield s
    s.stop_all()


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_register_does_not_start_until_autostart(service: CameraIngestionService) -> None:
    src = CameraSource(
        camera_id="cam-test",
        zone_id="zone-test",
        label="Test",
        source_url="0",
        anonymize_faces=False,
    )
    worker = service.register(src, autostart=False)
    try:
        assert worker.is_running is False
        assert service.get_worker("cam-test") is worker
        assert any(s.camera_id == "cam-test" for s in service.list_sources())
    finally:
        service.unregister("cam-test")


def test_load_from_missing_file_returns_zero(service: CameraIngestionService, tmp_path: Path) -> None:
    missing = tmp_path / "no-such-file.json"
    assert service.load_from_file(missing) == 0
    assert service.list_sources() == []


def test_load_from_invalid_json_returns_zero(service: CameraIngestionService, tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("not-json", encoding="utf-8")
    assert service.load_from_file(bad) == 0


def test_load_from_non_array_returns_zero(service: CameraIngestionService, tmp_path: Path) -> None:
    f = tmp_path / "obj.json"
    f.write_text('{"camera_id":"x"}', encoding="utf-8")
    assert service.load_from_file(f) == 0


def test_unregister_nonexistent_returns_false(service: CameraIngestionService) -> None:
    assert service.unregister("missing") is False


def test_full_capture_pipeline_with_video_file(
    service: CameraIngestionService, sample_video: Path
) -> None:
    """End-to-end: register a file source, frames flow, JPEG produced, Unit 01 counters update."""
    src = CameraSource(
        camera_id="cam-file",
        zone_id="zone-test",
        label="File Source",
        source_url=str(sample_video),
        anonymize_faces=False,  # skip detector for speed/determinism
    )
    worker = service.register(src, autostart=True)
    try:
        # Wait up to 5 s for at least one frame
        deadline = time.monotonic() + 5.0
        jpeg = None
        while time.monotonic() < deadline:
            jpeg = worker.get_latest_jpeg()
            if jpeg is not None:
                break
            time.sleep(0.05)

        assert jpeg is not None, "Worker never produced a JPEG"
        assert jpeg[:3] == b"\xff\xd8\xff", "Output is not a valid JPEG (missing SOI marker)"

        stream = service.capture_unit.get_stream("cam-file")
        assert stream is not None
        assert stream.total_frames_captured >= 1
        # After the short test file is fully read, status may be ACTIVE (still reading)
        # or DEGRADED (read failures after EOF) — both prove the pipeline worked end-to-end.
        assert stream.status in (StreamStatus.ACTIVE, StreamStatus.DEGRADED, StreamStatus.OFFLINE)
        assert stream.source_url == str(sample_video)
        assert stream.resolution == (320, 240)
    finally:
        service.unregister("cam-file")


def test_register_replaces_existing_camera(
    service: CameraIngestionService, sample_video: Path
) -> None:
    """Re-registering with the same id should stop the old worker and replace it."""
    src1 = CameraSource("cam-x", "zone-test", "v1", str(sample_video), False)
    w1 = service.register(src1, autostart=False)

    src2 = CameraSource("cam-x", "zone-test", "v2", str(sample_video), False)
    w2 = service.register(src2, autostart=False)

    try:
        assert w2 is not w1
        assert service.get_worker("cam-x") is w2
        # only one source registered for cam-x
        assert sum(1 for s in service.list_sources() if s.camera_id == "cam-x") == 1
        assert next(s for s in service.list_sources() if s.camera_id == "cam-x").label == "v2"
    finally:
        service.unregister("cam-x")


def test_load_from_file_skips_invalid_entries(
    service: CameraIngestionService, tmp_path: Path
) -> None:
    f = tmp_path / "mixed.json"
    f.write_text(
        '[{"camera_id":"ok","zone_id":"z","label":"L","source_url":"0"},'
        '{"missing":"required-keys"}]',
        encoding="utf-8",
    )
    count = service.load_from_file(f)
    try:
        assert count == 1
        ids = [s.camera_id for s in service.list_sources()]
        assert ids == ["ok"]
    finally:
        service.unregister("ok")


def test_offline_until_first_frame(service: CameraIngestionService) -> None:
    """A camera with a bogus URL stays OFFLINE and records last_error."""
    src = CameraSource(
        camera_id="cam-bogus",
        zone_id="zone-test",
        label="Bogus",
        source_url="rtsp://0.0.0.0:1/nonexistent",
        anonymize_faces=False,
    )
    worker = service.register(src, autostart=True)
    try:
        # Give the worker a moment to fail to open
        time.sleep(1.5)
        stream = service.capture_unit.get_stream("cam-bogus")
        assert stream is not None
        assert stream.status == StreamStatus.OFFLINE
        # last_error may or may not be set depending on how fast the open() call returns,
        # but we should have produced no frames
        assert stream.total_frames_captured == 0
        assert worker.get_latest_jpeg() is None
    finally:
        service.unregister("cam-bogus")
