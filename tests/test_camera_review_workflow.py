from datetime import datetime, timezone

import numpy as np
import pytest

from app.services.camera_event_intelligence import CameraEventIntelligenceEngine, ObjectDetection
from app.services.camera_event_pipeline import CameraEventPipeline, EventFrame
from app.services.camera_review_workflow import ReviewDecision, create_review_record


class FakeDetector:
    model_version = "review-test-v1"

    def detect(self, frame):
        return [ObjectDetection("person", 0.88, 2, 2, 18, 24)]


def candidate_batch():
    pipeline = CameraEventPipeline(CameraEventIntelligenceEngine(FakeDetector()))
    return pipeline.analyze_event(
        event_id="event-review-1",
        camera_id="camera-1",
        zone_id="entrance",
        frames=[EventFrame(np.zeros((32, 32, 3), dtype=np.uint8),
                           datetime(2026, 1, 1, tzinfo=timezone.utc))],
    )


def test_snapshot_uses_trigger_event_id_not_generated_frame_id():
    batch = candidate_batch()
    assert batch.snapshots[0].event_id == batch.event_id


@pytest.mark.parametrize("decision", list(ReviewDecision))
def test_review_record_captures_human_decision_without_changing_candidate(decision):
    batch = candidate_batch()
    record = create_review_record(
        batch,
        decision=decision,
        reviewer_user_id="principal-17",
        rationale="Reviewed the event context.",
        reviewed_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    assert record.event_id == batch.event_id
    assert record.reviewer_user_id == "principal-17"
    assert record.decision is decision
    assert record.source_status == "candidate"
    assert batch.status == "candidate"
    assert batch.requires_human_review is True


def test_review_requires_actor_rationale_and_aware_timestamp():
    batch = candidate_batch()
    with pytest.raises(ValueError, match="reviewer_user_id"):
        create_review_record(batch, decision=ReviewDecision.DISMISSED,
                             reviewer_user_id="", rationale="Reviewed")
    with pytest.raises(ValueError, match="rationale"):
        create_review_record(batch, decision=ReviewDecision.DISMISSED,
                             reviewer_user_id="u1", rationale=" ")
    with pytest.raises(ValueError, match="timezone-aware"):
        create_review_record(batch, decision=ReviewDecision.CONFIRMED,
                             reviewer_user_id="u1", rationale="Reviewed",
                             reviewed_at=datetime(2026, 1, 2))


def test_review_rejects_non_candidate_batch():
    batch = candidate_batch()
    from dataclasses import replace
    closed = replace(batch, status="closed")
    with pytest.raises(ValueError, match="candidate batches"):
        create_review_record(closed, decision=ReviewDecision.CONFIRMED,
                             reviewer_user_id="u1", rationale="Reviewed")
