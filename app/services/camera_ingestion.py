"""Live camera ingestion service.

Connects to real cameras (RTSP / HTTP MJPEG / USB / file) using OpenCV,
captures frames in background daemon threads, applies the Arab Data
Governance face-anonymization layer (Unit 14), updates the Video Capture
Unit (Unit 01) health counters, and exposes the latest JPEG snapshot for
HTTP / MJPEG streaming.

This module is designed to be safe to import even when no cameras are
configured — workers are only started after `register()` calls.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np

from app.core.config import settings
from app.core.governance_layer import anonymize_minor_faces
from app.core.runtime_settings import get_runtime_settings
from app.units.unit_01.module import StreamStatus, VideoCaptureUnit

logger = logging.getLogger(__name__)


# ── Data model ─────────────────────────────────────────────────────────────────


@dataclass
class CameraSource:
    """A user-configured camera source.

    Attributes:
        camera_id: Unique short identifier (e.g. ``"cam-gate"``).
        zone_id: Zone identifier from `seed_data.zones` (e.g. ``"zone-main-gate"``).
        label: Human-readable name shown in the UI.
        source_url: One of:
            - ``"rtsp://user:pass@ip:554/Streaming/Channels/101"``
            - ``"http://ip/video.mjpg"``
            - ``"0"`` / ``"1"`` (USB webcam index)
            - ``"./samples/clip.mp4"`` (local file, loops forever)
        anonymize_faces: When True (default), apply Unit 14 face blur on every
            frame before it is published / stored. Strongly recommended.
    """

    camera_id: str
    zone_id: str
    label: str
    source_url: str
    anonymize_faces: bool = True

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


# ── Background worker ──────────────────────────────────────────────────────────


class CameraStreamWorker:
    """Background thread that owns a single ``cv2.VideoCapture``.

    Maintains a single-slot latest-frame buffer (newer overwrites older)
    so streaming consumers always get the freshest JPEG and stale frames
    are dropped — exactly the behavior wanted for live monitoring.
    """

    def __init__(
        self,
        source: CameraSource,
        capture_unit: VideoCaptureUnit,
        jpeg_quality: int,
        max_fps: float,
        reconnect_seconds: float,
    ) -> None:
        self.source = source
        self._capture_unit = capture_unit
        self._jpeg_quality = max(1, min(100, int(jpeg_quality)))
        self._frame_interval = 1.0 / max(0.1, float(max_fps))
        self._reconnect_seconds = max(0.5, float(reconnect_seconds))

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._frame_lock = threading.Lock()
        self._latest_jpeg: bytes | None = None
        self._latest_frame_at: datetime | None = None
        self._frame_event = threading.Event()  # for low-latency MJPEG streaming

    # ── lifecycle ────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"cam-{self.source.camera_id}",
            daemon=True,
        )
        self._thread.start()
        logger.info("Camera worker started: %s -> %s", self.source.camera_id, self.source.source_url)

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
            self._thread = None
        logger.info("Camera worker stopped: %s", self.source.camera_id)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ── frame access ─────────────────────────────────────────────────────────

    def get_latest_jpeg(self) -> bytes | None:
        with self._frame_lock:
            return self._latest_jpeg

    def wait_next_frame(self, timeout: float = 5.0) -> bytes | None:
        """Block until a new frame is available, or timeout. Returns latest JPEG."""
        self._frame_event.clear()
        if self._frame_event.wait(timeout=timeout):
            return self.get_latest_jpeg()
        return self.get_latest_jpeg()  # may be stale or None

    # ── main loop ────────────────────────────────────────────────────────────

    def _open_capture(self) -> cv2.VideoCapture | None:
        """Open the OpenCV capture, handling URL / int / file uniformly."""
        url = self.source.source_url.strip()
        try:
            if url.isdigit():
                cap = cv2.VideoCapture(int(url))
            else:
                # Use FFMPEG backend explicitly for RTSP/HTTP — much more reliable on Windows
                if url.lower().startswith(("rtsp://", "http://", "https://")):
                    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                else:
                    cap = cv2.VideoCapture(url)
        except Exception as exc:  # pragma: no cover - cv2 rarely raises here
            logger.exception("VideoCapture construction failed: %s", exc)
            return None

        if not cap or not cap.isOpened():
            if cap is not None:
                cap.release()
            return None

        # Hint a small buffer to minimize live latency (best-effort, ignored by some backends)
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        return cap

    def _run(self) -> None:
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self._jpeg_quality]
        consecutive_failures = 0

        while not self._stop_event.is_set():
            cap = self._open_capture()
            if cap is None:
                self._mark_offline(f"Failed to open source {self.source.source_url!r}")
                if self._stop_event.wait(self._reconnect_seconds):
                    break
                continue

            logger.info("Camera %s connected", self.source.camera_id)
            consecutive_failures = 0
            last_emit_ts = 0.0

            try:
                while not self._stop_event.is_set():
                    ok, frame = cap.read()
                    if not ok or frame is None:
                        consecutive_failures += 1
                        self._capture_unit.get_stream(self.source.camera_id) and \
                            self._capture_unit.get_stream(self.source.camera_id).mark_frame_dropped()
                        if consecutive_failures >= 30:
                            self._mark_offline("Read failures exceeded threshold")
                            break
                        time.sleep(0.05)
                        continue

                    consecutive_failures = 0

                    # FPS throttle (so a 30fps source consumes <= max_fps CPU)
                    now = time.monotonic()
                    if now - last_emit_ts < self._frame_interval:
                        continue
                    last_emit_ts = now

                    # Apply Arab Governance Layer face anonymization (Unit 14)
                    if self.source.anonymize_faces:
                        try:
                            frame = anonymize_minor_faces(frame)
                        except Exception:
                            # Anonymization must never crash the ingestion loop;
                            # log and fall through with the raw frame.
                            logger.exception("Face anonymization failed for %s", self.source.camera_id)

                    # Encode JPEG
                    ok_enc, buf = cv2.imencode(".jpg", frame, encode_params)
                    if not ok_enc:
                        continue

                    jpeg_bytes = buf.tobytes()
                    captured_at = datetime.now(timezone.utc).replace(tzinfo=None)

                    with self._frame_lock:
                        self._latest_jpeg = jpeg_bytes
                        self._latest_frame_at = captured_at

                    # Update Unit 01 health counters
                    stream = self._capture_unit.get_stream(self.source.camera_id)
                    if stream is not None:
                        stream.mark_frame_received(at=captured_at)
                        # Update resolution from real captured size on first frame
                        h, w = frame.shape[:2]
                        if stream.resolution != (w, h):
                            stream.resolution = (w, h)

                    self._frame_event.set()
            finally:
                cap.release()

            # If we exit the inner loop and weren't stopped, we lost the connection — reconnect
            if not self._stop_event.is_set():
                if self._stop_event.wait(self._reconnect_seconds):
                    break

    # ── helpers ──────────────────────────────────────────────────────────────

    def _mark_offline(self, reason: str) -> None:
        logger.warning("Camera %s offline: %s", self.source.camera_id, reason)
        stream = self._capture_unit.get_stream(self.source.camera_id)
        if stream is not None:
            stream.mark_disconnected(error=reason)


# ── Service ────────────────────────────────────────────────────────────────────


class CameraIngestionService:
    """Lifecycle manager for all live camera workers."""

    def __init__(self, capture_unit: VideoCaptureUnit | None = None) -> None:
        self.capture_unit = capture_unit or VideoCaptureUnit()
        self._workers: dict[str, CameraStreamWorker] = {}
        self._sources: dict[str, CameraSource] = {}
        self._lock = threading.Lock()

    # ── registration ─────────────────────────────────────────────────────────

    def register(self, source: CameraSource, autostart: bool = True) -> CameraStreamWorker:
        with self._lock:
            if source.camera_id in self._workers:
                # idempotent: stop & replace
                self._workers[source.camera_id].stop()
                self.capture_unit.unregister_stream(source.camera_id)

            self.capture_unit.register_stream(
                camera_id=source.camera_id,
                location_id=source.zone_id,
                zone_label=source.label,
                source_url=source.source_url,
            )
            # Start in OFFLINE until first frame proves connectivity
            stream = self.capture_unit.get_stream(source.camera_id)
            if stream is not None:
                stream.status = StreamStatus.OFFLINE

            rt = get_runtime_settings()
            worker = CameraStreamWorker(
                source=source,
                capture_unit=self.capture_unit,
                jpeg_quality=rt.camera_jpeg_quality,
                max_fps=rt.camera_max_fps,
                reconnect_seconds=rt.camera_reconnect_seconds,
            )
            self._workers[source.camera_id] = worker
            self._sources[source.camera_id] = source

        if autostart:
            worker.start()
        self._persist_sources()
        return worker

    def unregister(self, camera_id: str) -> bool:
        with self._lock:
            worker = self._workers.pop(camera_id, None)
            self._sources.pop(camera_id, None)
        if worker is not None:
            worker.stop()
            self.capture_unit.unregister_stream(camera_id)
            self._persist_sources()
            return True
        return False

    # ── queries ──────────────────────────────────────────────────────────────

    def list_sources(self) -> list[CameraSource]:
        with self._lock:
            return list(self._sources.values())

    def get_worker(self, camera_id: str) -> CameraStreamWorker | None:
        with self._lock:
            return self._workers.get(camera_id)

    def get_latest_jpeg(self, camera_id: str) -> bytes | None:
        worker = self.get_worker(camera_id)
        return worker.get_latest_jpeg() if worker else None

    # ── group lifecycle ──────────────────────────────────────────────────────

    def start_all(self) -> None:
        for worker in list(self._workers.values()):
            worker.start()

    def stop_all(self) -> None:
        for worker in list(self._workers.values()):
            worker.stop()

    # ── persistence ──────────────────────────────────────────────────────────

    def _persist_sources(self) -> None:
        """Write the current set of sources to the configured cameras file.

        Called automatically after every register / unregister. Safe to call
        before a file exists — the parent directory is created if needed.
        Failures are logged but never raised, so a transient disk problem
        cannot break the HTTP request that triggered the save.
        """
        try:
            path = Path(settings.camera_sources_file)
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = [src.to_dict() for src in self._sources.values()]
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            logger.exception("Failed to persist camera sources")

    # ── bulk loading ─────────────────────────────────────────────────────────

    def load_from_file(self, path: str | Path) -> int:
        """Load camera sources from a JSON file. Returns count loaded.

        Silently returns 0 if the file does not exist (clean fall-back to demo mode).
        """
        p = Path(path)
        if not p.exists():
            logger.info("Camera sources file not found at %s — skipping live ingestion.", p)
            return 0
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error("Failed to parse %s: %s", p, exc)
            return 0
        if not isinstance(payload, list):
            logger.error("Camera sources file %s must contain a JSON array.", p)
            return 0

        count = 0
        for entry in payload:
            try:
                source = CameraSource(
                    camera_id=str(entry["camera_id"]),
                    zone_id=str(entry["zone_id"]),
                    label=str(entry["label"]),
                    source_url=str(entry["source_url"]),
                    anonymize_faces=bool(entry.get("anonymize_faces", settings.camera_anonymize_faces)),
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.error("Skipping invalid camera entry %r: %s", entry, exc)
                continue
            self.register(source, autostart=True)
            count += 1
        logger.info("Loaded %d live camera source(s) from %s", count, p)
        return count


# ── Module-level singleton ────────────────────────────────────────────────────

# Reuses the same VideoCaptureUnit instance referenced by units endpoint via
# late binding (the units endpoint creates its own; that is fine — they share
# the same module-level dataclass type and we expose this one for live ops).
ingestion_service = CameraIngestionService()
