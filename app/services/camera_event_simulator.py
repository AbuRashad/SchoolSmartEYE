"""Deterministic synthetic camera-event generator for offline testing.

This module generates metadata only. It never opens a camera, reads a video,
captures images, or represents an identified person.
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Iterator, Sequence

EVENT_TYPES = (
    "crowd_density_spike",
    "restricted_zone_entry",
    "unusual_dwell_time",
    "camera_signal_loss",
)
SEVERITIES = ("low", "medium", "high")


def generate_camera_events(
    camera_ids: Sequence[str],
    *,
    events_per_camera: int = 10,
    seed: int = 7,
    run_id: str = "simulation",
    start_at: datetime | None = None,
) -> Iterator[dict[str, object]]:
    """Yield repeatable, privacy-minimised event payloads for API/load tests."""
    if not camera_ids:
        raise ValueError("At least one camera_id is required")
    if events_per_camera < 1 or events_per_camera > 10_000:
        raise ValueError("events_per_camera must be between 1 and 10000")
    if any(not camera_id or len(camera_id) > 64 for camera_id in camera_ids):
        raise ValueError("camera_ids must be non-empty strings up to 64 characters")

    rng = random.Random(seed)
    base_time = start_at or datetime.now(timezone.utc)
    if base_time.tzinfo is None or base_time.utcoffset() is None:
        raise ValueError("start_at must be timezone-aware")
    base_time = base_time.astimezone(timezone.utc)
    for camera_index, camera_id in enumerate(camera_ids):
        for sequence in range(events_per_camera):
            event_type = EVENT_TYPES[(camera_index + sequence) % len(EVENT_TYPES)]
            detected_at = base_time + timedelta(milliseconds=(camera_index * events_per_camera + sequence) * 25)
            yield {
                "idempotency_key": f"sim-{run_id}-{camera_id}-{sequence:05d}"[:128],
                "camera_id": camera_id,
                "zone_id": f"synthetic-zone-{camera_index + 1}",
                "event_type": event_type,
                "severity": rng.choice(SEVERITIES),
                "confidence": round(rng.uniform(0.55, 0.99), 3),
                "detected_at": detected_at.isoformat(),
                "evidence_ref": f"synthetic://{uuid.uuid5(uuid.NAMESPACE_URL, f'{run_id}/{camera_id}/{sequence}')}",
            }
