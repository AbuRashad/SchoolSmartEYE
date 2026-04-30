"""Tests for Unit 15: Pedagogical Behavioral Intelligence Agent.

Covers:
- EngagementSnapshot recording and retrieval
- Behavioral history queries
- Engagement summary computation (avg score, dominant state, trend)
- Session insights generation (top engaged, flags, mismatches)
- Teacher feedback recording and metrics
- Daily baseline harvesting
- API endpoints: GET /agent/insights, POST /agent/feedback,
  GET /agent/feedback/metrics, GET /agent/baselines,
  GET /students/{id}/behavioral-history
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models import AgentFeedback, EngagementSnapshot, EngagementState
from app.services import seed_data
from app.services.pedagogical_agent import (
    PedagogicalAgentService,
    StudentEngagementSummary,
    default_score_for,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _make_service(
    snapshots: list[EngagementSnapshot] | None = None,
    feedback: list[AgentFeedback] | None = None,
) -> PedagogicalAgentService:
    return PedagogicalAgentService(
        snapshots=snapshots if snapshots is not None else [],
        feedback_log=feedback if feedback is not None else [],
    )


# ── Unit tests — PedagogicalAgentService ─────────────────────────────────────


class TestDefaultScoreFor:
    def test_engaged_is_highest(self) -> None:
        assert default_score_for(EngagementState.ENGAGED) > default_score_for(EngagementState.ATTENTIVE)

    def test_drowsy_is_lowest(self) -> None:
        assert default_score_for(EngagementState.DROWSY) < default_score_for(EngagementState.DISTRACTED)

    def test_all_scores_in_range(self) -> None:
        for state in EngagementState:
            score = default_score_for(state)
            assert 0.0 <= score <= 1.0


class TestRecordSnapshot:
    def test_snapshot_is_persisted(self) -> None:
        snapshots: list[EngagementSnapshot] = []
        svc = _make_service(snapshots)
        svc.record_snapshot("STU-001", EngagementState.ENGAGED, session_id="SES-1")
        assert len(snapshots) == 1
        assert snapshots[0].student_id == "STU-001"
        assert snapshots[0].state == EngagementState.ENGAGED

    def test_custom_score_is_stored(self) -> None:
        svc = _make_service()
        snap = svc.record_snapshot(
            "STU-001", EngagementState.ATTENTIVE, session_id="SES-1", score=0.65
        )
        assert snap.score == pytest.approx(0.65)

    def test_score_out_of_range_is_clipped(self) -> None:
        svc = _make_service()
        snap = svc.record_snapshot("STU-001", EngagementState.ENGAGED, session_id="SES-1", score=2.5)
        assert snap.score == pytest.approx(1.0)

    def test_audio_context_and_mismatch_stored(self) -> None:
        svc = _make_service()
        snap = svc.record_snapshot(
            "STU-001", EngagementState.DISTRACTED, session_id="SES-1",
            audio_context="speaking", audio_visual_mismatch=True,
        )
        assert snap.audio_context == "speaking"
        assert snap.audio_visual_mismatch is True

    def test_recorded_at_defaults_to_now(self) -> None:
        before = _utcnow()
        svc = _make_service()
        snap = svc.record_snapshot("STU-001", EngagementState.ATTENTIVE, session_id="SES-1")
        after = _utcnow()
        assert before <= snap.recorded_at <= after

    def test_explicit_recorded_at_is_respected(self) -> None:
        ts = datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc)
        svc = _make_service()
        snap = svc.record_snapshot(
            "STU-001", EngagementState.ENGAGED, session_id="SES-1", recorded_at=ts
        )
        assert snap.recorded_at == ts


class TestGetBehavioralHistory:
    def test_returns_snapshots_for_student(self) -> None:
        svc = _make_service()
        svc.record_snapshot("STU-001", EngagementState.ENGAGED, session_id="SES-1")
        svc.record_snapshot("STU-002", EngagementState.DROWSY, session_id="SES-1")
        history = svc.get_behavioral_history("STU-001")
        assert all(s.student_id == "STU-001" for s in history)
        assert len(history) == 1

    def test_respects_days_cutoff(self) -> None:
        old_ts = _utcnow() - timedelta(days=40)
        recent_ts = _utcnow() - timedelta(days=5)
        svc = _make_service()
        svc.record_snapshot("STU-001", EngagementState.DISTRACTED, "SES-OLD", recorded_at=old_ts)
        svc.record_snapshot("STU-001", EngagementState.ENGAGED, "SES-NEW", recorded_at=recent_ts)
        history = svc.get_behavioral_history("STU-001", days=30)
        assert len(history) == 1
        assert history[0].session_id == "SES-NEW"

    def test_results_are_newest_first(self) -> None:
        svc = _make_service()
        for i in range(5):
            ts = _utcnow() - timedelta(hours=i)
            svc.record_snapshot("STU-001", EngagementState.ATTENTIVE, "SES-1", recorded_at=ts)
        history = svc.get_behavioral_history("STU-001")
        for i in range(len(history) - 1):
            assert history[i].recorded_at >= history[i + 1].recorded_at

    def test_returns_empty_for_unknown_student(self) -> None:
        svc = _make_service()
        assert svc.get_behavioral_history("GHOST") == []


class TestGetEngagementSummary:
    def test_returns_none_when_no_data(self) -> None:
        svc = _make_service()
        assert svc.get_engagement_summary("STU-001") is None

    def test_avg_score_computed_correctly(self) -> None:
        svc = _make_service()
        scores = [0.8, 0.6, 0.4]
        for score in scores:
            svc.record_snapshot("STU-001", EngagementState.ATTENTIVE, "SES-1", score=score)
        summary = svc.get_engagement_summary("STU-001")
        assert summary is not None
        assert summary.avg_score_7d == pytest.approx(sum(scores) / len(scores), abs=1e-3)

    def test_dominant_state_is_most_frequent(self) -> None:
        svc = _make_service()
        svc.record_snapshot("STU-001", EngagementState.ENGAGED, "SES-1")
        svc.record_snapshot("STU-001", EngagementState.ENGAGED, "SES-1")
        svc.record_snapshot("STU-001", EngagementState.DISTRACTED, "SES-1")
        summary = svc.get_engagement_summary("STU-001")
        assert summary is not None
        assert summary.dominant_state == EngagementState.ENGAGED.value

    def test_trend_improving_when_score_increases(self) -> None:
        svc = _make_service()
        # older snapshots (lower score), newer snapshots (higher score)
        base = _utcnow() - timedelta(days=6)
        for i in range(6):
            ts = base + timedelta(days=i)
            score = 0.3 + i * 0.1  # 0.3 → 0.8
            svc.record_snapshot("STU-001", EngagementState.ATTENTIVE, "SES-1", score=score, recorded_at=ts)
        summary = svc.get_engagement_summary("STU-001")
        assert summary is not None
        assert summary.trend == "improving"

    def test_trend_declining_when_score_decreases(self) -> None:
        svc = _make_service()
        base = _utcnow() - timedelta(days=6)
        for i in range(6):
            ts = base + timedelta(days=i)
            score = 0.9 - i * 0.12  # 0.9 → ~0.3
            svc.record_snapshot("STU-001", EngagementState.ATTENTIVE, "SES-1", score=score, recorded_at=ts)
        summary = svc.get_engagement_summary("STU-001")
        assert summary is not None
        assert summary.trend == "declining"

    def test_mismatch_count_correct(self) -> None:
        svc = _make_service()
        svc.record_snapshot("STU-001", EngagementState.DISTRACTED, "SES-1",
                             audio_visual_mismatch=True)
        svc.record_snapshot("STU-001", EngagementState.ENGAGED, "SES-1",
                             audio_visual_mismatch=False)
        summary = svc.get_engagement_summary("STU-001")
        assert summary is not None
        assert summary.mismatch_count_7d == 1

    def test_to_dict_has_expected_keys(self) -> None:
        svc = _make_service()
        svc.record_snapshot("STU-001", EngagementState.ENGAGED, "SES-1")
        summary = svc.get_engagement_summary("STU-001")
        assert summary is not None
        d = summary.to_dict()
        assert set(d.keys()) == {
            "avg_score_7d", "dominant_state", "trend",
            "total_snapshots_7d", "mismatch_count_7d",
        }


class TestGetSessionInsights:
    def test_empty_returns_empty_insight(self) -> None:
        svc = _make_service()
        result = svc.get_session_insights()
        assert result["session_id"] is None
        assert result["top_engaged_students"] == []
        assert result["disengagement_flags"] == []

    def test_most_recent_session_is_default(self) -> None:
        svc = _make_service()
        svc.record_snapshot("STU-001", EngagementState.ENGAGED, "SES-OLD",
                             recorded_at=_utcnow() - timedelta(hours=2))
        svc.record_snapshot("STU-002", EngagementState.ATTENTIVE, "SES-NEW",
                             recorded_at=_utcnow())
        result = svc.get_session_insights()
        assert result["session_id"] == "SES-NEW"

    def test_top_engaged_sorted_by_score(self) -> None:
        svc = _make_service()
        svc.record_snapshot("STU-001", EngagementState.ENGAGED, "SES-1", score=0.9)
        svc.record_snapshot("STU-002", EngagementState.ATTENTIVE, "SES-1", score=0.7)
        svc.record_snapshot("STU-003", EngagementState.DROWSY, "SES-1", score=0.2)
        result = svc.get_session_insights("SES-1")
        top = result["top_engaged_students"]
        assert isinstance(top, list)
        assert top[0]["student_id"] == "STU-001"

    def test_disengagement_flags_include_distracted_and_drowsy(self) -> None:
        svc = _make_service()
        svc.record_snapshot("STU-001", EngagementState.DISTRACTED, "SES-1")
        svc.record_snapshot("STU-002", EngagementState.DROWSY, "SES-1")
        svc.record_snapshot("STU-003", EngagementState.ENGAGED, "SES-1")
        result = svc.get_session_insights("SES-1")
        flags = {f["student_id"] for f in result["disengagement_flags"]}
        assert "STU-001" in flags
        assert "STU-002" in flags
        assert "STU-003" not in flags

    def test_audio_visual_mismatches_detected(self) -> None:
        svc = _make_service()
        svc.record_snapshot("STU-001", EngagementState.DISTRACTED, "SES-1",
                             audio_context="speaking", audio_visual_mismatch=True)
        svc.record_snapshot("STU-002", EngagementState.ENGAGED, "SES-1",
                             audio_context="speaking", audio_visual_mismatch=False)
        result = svc.get_session_insights("SES-1")
        mismatches = [m["student_id"] for m in result["audio_visual_mismatches"]]
        assert "STU-001" in mismatches
        assert "STU-002" not in mismatches

    def test_class_average_computed(self) -> None:
        svc = _make_service()
        svc.record_snapshot("STU-001", EngagementState.ENGAGED, "SES-1", score=0.8)
        svc.record_snapshot("STU-002", EngagementState.ATTENTIVE, "SES-1", score=0.6)
        result = svc.get_session_insights("SES-1")
        assert result["class_engagement_average"] == pytest.approx(0.7, abs=1e-3)

    def test_unknown_session_returns_empty(self) -> None:
        svc = _make_service()
        svc.record_snapshot("STU-001", EngagementState.ENGAGED, "SES-1")
        result = svc.get_session_insights("SES-GHOST")
        assert result["session_id"] is None


class TestFeedbackAndMetrics:
    def test_record_feedback_stored(self) -> None:
        feedback: list[AgentFeedback] = []
        svc = _make_service(feedback=feedback)
        svc.record_feedback(
            "FB-1", "SES-1", "STU-001",
            EngagementState.DISTRACTED, EngagementState.ENGAGED,
            "Teacher correction",
        )
        assert len(feedback) == 1
        assert feedback[0].feedback_id == "FB-1"

    def test_metrics_empty_when_no_feedback(self) -> None:
        svc = _make_service()
        m = svc.compute_feedback_metrics()
        assert m["total_feedback"] == 0
        assert m["accuracy"] is None

    def test_accuracy_computed_correctly(self) -> None:
        svc = _make_service()
        # 2 correct, 1 wrong = 66.7%
        svc.record_feedback("FB-1", "SES-1", "STU-001",
                             EngagementState.ENGAGED, EngagementState.ENGAGED, "")
        svc.record_feedback("FB-2", "SES-1", "STU-002",
                             EngagementState.ENGAGED, EngagementState.ENGAGED, "")
        svc.record_feedback("FB-3", "SES-1", "STU-003",
                             EngagementState.DISTRACTED, EngagementState.ENGAGED, "")
        m = svc.compute_feedback_metrics()
        assert m["total_feedback"] == 3
        assert m["correct_predictions"] == 2
        assert m["accuracy"] == pytest.approx(2 / 3, abs=1e-3)


class TestDailyBaselines:
    def test_baselines_keyed_by_student_and_date(self) -> None:
        svc = _make_service()
        ts = datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc)
        svc.record_snapshot("STU-001", EngagementState.ENGAGED, "SES-1", score=0.8, recorded_at=ts)
        svc.record_snapshot("STU-001", EngagementState.ATTENTIVE, "SES-1", score=0.6, recorded_at=ts)
        baselines = svc.compute_daily_baselines()
        assert "STU-001" in baselines
        assert "2026-04-01" in baselines["STU-001"]
        assert baselines["STU-001"]["2026-04-01"] == pytest.approx(0.7, abs=1e-3)

    def test_get_baselines_returns_cached(self) -> None:
        svc = _make_service()
        svc.record_snapshot("STU-001", EngagementState.ENGAGED, "SES-1", score=0.9)
        svc.compute_daily_baselines()
        baselines = svc.get_baselines()
        assert "STU-001" in baselines


# ── API integration tests ─────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure seed data is populated before each test."""
    seed_data.populate()


@pytest.mark.anyio
async def test_get_agent_insights_returns_session_data() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/agent/insights")
    assert r.status_code == 200
    data = r.json()
    assert "class_engagement_average" in data
    assert "top_engaged_students" in data
    assert "disengagement_flags" in data
    assert "audio_visual_mismatches" in data
    assert isinstance(data["top_engaged_students"], list)


@pytest.mark.anyio
async def test_get_agent_insights_with_explicit_session() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/agent/insights?session_id=SES-TODAY-AM")
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"] == "SES-TODAY-AM"


@pytest.mark.anyio
async def test_post_agent_feedback_created() -> None:
    transport = ASGITransport(app=app)
    payload = {
        "session_id": "SES-TODAY-AM",
        "student_id": "STU-2024-0847",
        "predicted_state": "engaged",
        "confirmed_state": "engaged",
        "teacher_notes": "Accurate prediction",
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v1/agent/feedback", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["session_id"] == "SES-TODAY-AM"
    assert data["student_id"] == "STU-2024-0847"
    assert data["feedback_id"].startswith("FB-")


@pytest.mark.anyio
async def test_post_agent_feedback_unknown_student_returns_404() -> None:
    transport = ASGITransport(app=app)
    payload = {
        "session_id": "SES-1",
        "student_id": "STU-GHOST",
        "predicted_state": "engaged",
        "confirmed_state": "attentive",
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/v1/agent/feedback", json=payload)
    assert r.status_code == 404


@pytest.mark.anyio
async def test_get_agent_feedback_metrics() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/agent/feedback/metrics")
    assert r.status_code == 200
    data = r.json()
    assert "total_feedback" in data
    assert data["total_feedback"] >= 3  # seeded feedback entries


@pytest.mark.anyio
async def test_get_agent_baselines() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/agent/baselines")
    assert r.status_code == 200
    data = r.json()
    assert "baselines" in data
    assert "total_students" in data
    assert data["total_students"] > 0


@pytest.mark.anyio
async def test_student_behavioral_history_returns_snapshots() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/students/STU-2024-0847/behavioral-history")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    first = data[0]
    assert first["student_id"] == "STU-2024-0847"
    assert "state" in first
    assert "score" in first
    assert "session_id" in first


@pytest.mark.anyio
async def test_student_behavioral_history_unknown_student_returns_404() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/students/STU-GHOST/behavioral-history")
    assert r.status_code == 404


@pytest.mark.anyio
async def test_student_behavioral_history_invalid_days_returns_400() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/students/STU-2024-0847/behavioral-history?days=0")
    assert r.status_code == 400


@pytest.mark.anyio
async def test_student_profile_includes_engagement_summary() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/students/STU-2024-0847/profile")
    assert r.status_code == 200
    data = r.json()
    assert "engagement_summary" in data
    eng = data["engagement_summary"]
    assert eng is not None
    assert "avg_score_7d" in eng
    assert "dominant_state" in eng
    assert "trend" in eng
    assert "total_snapshots_7d" in eng
    assert "mismatch_count_7d" in eng


@pytest.mark.anyio
async def test_units_endpoint_includes_unit_15() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/units")
    assert r.status_code == 200
    units = r.json()
    unit_ids = [u["unit_id"] for u in units]
    assert 15 in unit_ids
    unit_15 = next(u for u in units if u["unit_id"] == 15)
    assert "Pedagogical" in unit_15["name"]
