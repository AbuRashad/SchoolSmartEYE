"""CPU-first camera CV scheduling primitives.

This module deliberately contains no model weights and performs no inference.
It provides bounded frame scheduling so a later detector/tracker can be added
without allowing stale frames or a busy camera to create unbounded work.
"""
from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class CameraCVConfig:
    """Per-camera CPU workload limits; values are safe defaults, not benchmarks."""

    sample_interval_seconds: float = 1.0
    max_width: int = 640
    max_height: int = 360
    max_pending_frames: int = 2
    max_concurrent_inference_jobs: int = 1

    def __post_init__(self) -> None:
        if self.sample_interval_seconds <= 0:
            raise ValueError("sample_interval_seconds must be positive")
        if self.max_width < 1 or self.max_height < 1:
            raise ValueError("frame dimensions must be positive")
        if self.max_pending_frames < 1:
            raise ValueError("max_pending_frames must be at least 1")
        if self.max_concurrent_inference_jobs < 1:
            raise ValueError("max_concurrent_inference_jobs must be at least 1")


class FrameSamplingGate:
    """Thread-safe monotonic-time gate for per-camera frame sampling."""

    def __init__(self, interval_seconds: float, clock=time.monotonic) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self.interval_seconds = float(interval_seconds)
        self._clock = clock
        self._last_accepted: float | None = None
        self._lock = threading.Lock()

    def should_accept(self, now: float | None = None) -> bool:
        current = self._clock() if now is None else float(now)
        with self._lock:
            if self._last_accepted is None or current - self._last_accepted >= self.interval_seconds:
                self._last_accepted = current
                return True
            return False

    def reset(self) -> None:
        with self._lock:
            self._last_accepted = None


class LatestFrameQueue(Generic[T]):
    """Bounded queue that drops the oldest pending frame when overloaded.

    This favors fresh scene state over processing a growing backlog. The caller
    must separately record dropped-frame metrics and processing lag.
    """

    def __init__(self, maxsize: int = 2) -> None:
        if maxsize < 1:
            raise ValueError("maxsize must be at least 1")
        self._queue: queue.Queue[T] = queue.Queue(maxsize=maxsize)
        self._lock = threading.Lock()
        self.dropped_count = 0

    def put_latest(self, item: T) -> None:
        with self._lock:
            if self._queue.full():
                try:
                    self._queue.get_nowait()
                    self.dropped_count += 1
                except queue.Empty:  # pragma: no cover - guarded by lock
                    pass
            self._queue.put_nowait(item)

    def get(self, timeout: float | None = None) -> T:
        return self._queue.get(timeout=timeout)

    def get_nowait(self) -> T:
        return self._queue.get_nowait()

    @property
    def pending_count(self) -> int:
        return self._queue.qsize()

    @property
    def maxsize(self) -> int:
        return self._queue.maxsize
