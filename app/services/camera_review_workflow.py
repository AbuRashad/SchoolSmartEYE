"""Human-review decision contract for camera candidate batches.

Pure domain logic only: persistence, authentication, school authorization and
audit writes belong in the API/service layer after tenant scope is enforced.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from app.services.camera_event_pipeline import CameraEventBatch


class ReviewDecision(str, Enum):
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    NEEDS_FOLLOW_UP = "needs_follow_up"


@dataclass(frozen=True)
class CameraReviewRecord:
    review_id: str
    event_id: str
    camera_id: str
    zone_id: str
    decision: ReviewDecision
    reviewer_user_id: str
    reviewed_at: str
    rationale: str
    source_status: str = "candidate"


def create_review_record(
    batch: CameraEventBatch,
    *,
    decision: ReviewDecision,
    reviewer_user_id: str,
    rationale: str,
    reviewed_at: datetime | None = None,
) -> CameraReviewRecord:
    """Record a human decision without mutating or upgrading the AI candidate."""
    if not batch.requires_human_review or batch.status != "candidate":
        raise ValueError("only candidate batches requiring human review can be reviewed")
    if not reviewer_user_id.strip():
        raise ValueError("reviewer_user_id is required")
    if not rationale.strip():
        raise ValueError("a rationale is required for every review decision")

    timestamp = reviewed_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("reviewed_at must be timezone-aware")

    return CameraReviewRecord(
        review_id=uuid4().hex,
        event_id=batch.event_id,
        camera_id=batch.camera_id,
        zone_id=batch.zone_id,
        decision=ReviewDecision(decision),
        reviewer_user_id=reviewer_user_id,
        reviewed_at=timestamp.astimezone(timezone.utc).isoformat(),
        rationale=rationale.strip(),
    )
