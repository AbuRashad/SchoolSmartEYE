"""Unit 15: Pedagogical Behavioral Intelligence Agent — core service.

Analyses per-student engagement state (pose / audio) across class sessions,
maintains long-term behavioral memory, exposes session insights, and runs a
nightly baseline harvesting pass to continuously refine per-student profiles.

All storage is in-memory (same pattern as the rest of the system). Feedback
entries are also written to an append-only JSONL file in `video_log_dir` when
the directory exists.
"""
from __future__ import annotations

import json
import os
import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from app.models import AgentFeedback, EngagementSnapshot, EngagementState


# ── Engagement scoring helpers ────────────────────────────────────────────────

_STATE_SCORES: dict[EngagementState, float] = {
    EngagementState.ENGAGED: 0.95,
    EngagementState.ATTENTIVE: 0.75,
    EngagementState.UNKNOWN: 0.50,
    EngagementState.DISTRACTED: 0.30,
    EngagementState.DROWSY: 0.15,
}

_POSITIVE_STATES = {EngagementState.ENGAGED, EngagementState.ATTENTIVE}
_NEGATIVE_STATES = {EngagementState.DISTRACTED, EngagementState.DROWSY}


def default_score_for(state: EngagementState) -> float:
    return _STATE_SCORES.get(state, 0.5)


# ── Insight data structures (plain dicts for API serialisation) ───────────────


class StudentEngagementSummary:
    """Per-student engagement summary returned inside StudentProfile."""

    __slots__ = (
        "avg_score_7d",
        "dominant_state",
        "trend",
        "total_snapshots_7d",
        "mismatch_count_7d",
    )

    def __init__(
        self,
        avg_score_7d: float,
        dominant_state: str,
        trend: str,
        total_snapshots_7d: int,
        mismatch_count_7d: int,
    ) -> None:
        self.avg_score_7d = avg_score_7d
        self.dominant_state = dominant_state
        self.trend = trend
        self.total_snapshots_7d = total_snapshots_7d
        self.mismatch_count_7d = mismatch_count_7d

    def to_dict(self) -> dict[str, object]:
        return {
            "avg_score_7d": round(self.avg_score_7d, 3),
            "dominant_state": self.dominant_state,
            "trend": self.trend,
            "total_snapshots_7d": self.total_snapshots_7d,
            "mismatch_count_7d": self.mismatch_count_7d,
        }


# ── Main service ──────────────────────────────────────────────────────────────


class PedagogicalAgentService:
    """Centralised service for Unit 15 — Pedagogical Behavioral Intelligence.

    Thread-safe via a module-level lock (same pattern as students endpoint).
    """

    def __init__(
        self,
        snapshots: list[EngagementSnapshot],
        feedback_log: list[AgentFeedback],
        *,
        video_log_dir: Optional[str] = None,
    ) -> None:
        self._snapshots = snapshots
        self._feedback_log = feedback_log
        self._video_log_dir = video_log_dir
        self._lock = threading.Lock()

        # Cached per-student daily baselines: {student_id: {date_str: avg_score}}
        self._baselines: dict[str, dict[str, float]] = {}

    # ── Recording ─────────────────────────────────────────────────────────────

    def record_snapshot(
        self,
        student_id: str,
        state: EngagementState,
        session_id: str,
        score: Optional[float] = None,
        zone_id: Optional[str] = None,
        audio_context: Optional[str] = None,
        audio_visual_mismatch: bool = False,
        recorded_at: Optional[datetime] = None,
    ) -> EngagementSnapshot:
        if score is None:
            score = default_score_for(state)
        score = max(0.0, min(1.0, score))
        snapshot = EngagementSnapshot(
            student_id=student_id,
            recorded_at=recorded_at or datetime.now(timezone.utc),
            state=state,
            score=score,
            session_id=session_id,
            zone_id=zone_id,
            audio_context=audio_context,
            audio_visual_mismatch=audio_visual_mismatch,
        )
        with self._lock:
            self._snapshots.append(snapshot)
        return snapshot

    def record_feedback(
        self,
        feedback_id: str,
        session_id: str,
        student_id: str,
        predicted_state: EngagementState,
        confirmed_state: EngagementState,
        teacher_notes: str = "",
    ) -> AgentFeedback:
        entry = AgentFeedback(
            feedback_id=feedback_id,
            session_id=session_id,
            student_id=student_id,
            predicted_state=predicted_state,
            confirmed_state=confirmed_state,
            teacher_notes=teacher_notes,
            recorded_at=datetime.now(timezone.utc),
        )
        with self._lock:
            self._feedback_log.append(entry)

        # Append to JSONL file if log directory is configured
        if self._video_log_dir:
            self._append_feedback_jsonl(entry)

        return entry

    def _append_feedback_jsonl(self, entry: AgentFeedback) -> None:
        try:
            log_path = Path(self._video_log_dir) / "agent_performance.jsonl"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "feedback_id": entry.feedback_id,
                "session_id": entry.session_id,
                "student_id": entry.student_id,
                "predicted_state": entry.predicted_state.value,
                "confirmed_state": entry.confirmed_state.value,
                "teacher_notes": entry.teacher_notes,
                "recorded_at": entry.recorded_at.isoformat(),
            }
            with open(log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            pass  # non-fatal: log directory may not exist in all environments

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_behavioral_history(
        self,
        student_id: str,
        days: int = 30,
    ) -> list[EngagementSnapshot]:
        """Return snapshots for a student, newest-first, within the last N days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        with self._lock:
            return sorted(
                [
                    s for s in self._snapshots
                    if s.student_id == student_id and s.recorded_at >= cutoff
                ],
                key=lambda s: s.recorded_at,
                reverse=True,
            )

    def get_engagement_summary(self, student_id: str) -> Optional[StudentEngagementSummary]:
        """Return a 7-day engagement summary for one student, or None if no data."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        with self._lock:
            recent = [
                s for s in self._snapshots
                if s.student_id == student_id and s.recorded_at >= cutoff
            ]
        if not recent:
            return None

        avg_score = sum(s.score for s in recent) / len(recent)
        mismatch_count = sum(1 for s in recent if s.audio_visual_mismatch)

        # Dominant state by frequency
        state_counts: dict[EngagementState, int] = defaultdict(int)
        for s in recent:
            state_counts[s.state] += 1
        dominant_state = max(state_counts, key=lambda st: state_counts[st]).value

        # Trend: compare first-half (newer) vs second-half (older) of the window.
        # Sort newest-first so [:half] always represents the more recent readings.
        recent_sorted = sorted(recent, key=lambda s: s.recorded_at, reverse=True)
        half = len(recent_sorted) // 2
        if half < 1:
            trend = "stable"
        else:
            newer_avg = sum(s.score for s in recent_sorted[:half]) / half
            older_avg = sum(s.score for s in recent_sorted[half:]) / max(len(recent_sorted) - half, 1)
            diff = newer_avg - older_avg
            trend = "improving" if diff > 0.05 else "declining" if diff < -0.05 else "stable"

        return StudentEngagementSummary(
            avg_score_7d=avg_score,
            dominant_state=dominant_state,
            trend=trend,
            total_snapshots_7d=len(recent),
            mismatch_count_7d=mismatch_count,
        )

    def get_session_insights(self, session_id: Optional[str] = None) -> dict[str, object]:
        """Return an AI session summary suitable for the Agent Insights API endpoint.

        If `session_id` is None the most recent session is used.
        """
        with self._lock:
            if not self._snapshots:
                return self._empty_insights()

            # Resolve session
            if session_id is None:
                session_id = max(self._snapshots, key=lambda s: s.recorded_at).session_id

            session_snaps = [s for s in self._snapshots if s.session_id == session_id]

        if not session_snaps:
            return self._empty_insights()

        # Per-student latest snapshot in the session
        latest: dict[str, EngagementSnapshot] = {}
        for snap in sorted(session_snaps, key=lambda s: s.recorded_at):
            latest[snap.student_id] = snap

        # Class-level average
        class_avg = sum(s.score for s in latest.values()) / max(len(latest), 1)

        # Top engaged (descending by score, up to 5)
        top_engaged = sorted(latest.values(), key=lambda s: s.score, reverse=True)[:5]

        # Disengagement flags
        flagged = [s for s in latest.values() if s.state in _NEGATIVE_STATES]

        # Audio-visual mismatches
        mismatches = [s for s in latest.values() if s.audio_visual_mismatch]

        # Improvement note from recent feedback
        improvement_note = self._derive_improvement_note()

        return {
            "session_id": session_id,
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "class_engagement_average": round(class_avg, 3),
            "top_engaged_students": [
                {
                    "student_id": s.student_id,
                    "score": round(s.score, 3),
                    "state": s.state.value,
                }
                for s in top_engaged
            ],
            "disengagement_flags": [
                {
                    "student_id": s.student_id,
                    "state": s.state.value,
                    "score": round(s.score, 3),
                    "zone_id": s.zone_id,
                    "since": s.recorded_at.isoformat(),
                }
                for s in flagged
            ],
            "audio_visual_mismatches": [
                {
                    "student_id": s.student_id,
                    "audio_context": s.audio_context,
                    "visual_state": s.state.value,
                    "score": round(s.score, 3),
                }
                for s in mismatches
            ],
            "improvement_note": improvement_note,
        }

    # ── Daily knowledge harvesting ─────────────────────────────────────────────

    def compute_daily_baselines(self) -> dict[str, dict[str, float]]:
        """Recompute per-student daily engagement averages from all snapshots.

        Returns a nested dict: {student_id: {date_iso: avg_score}}.
        Called nightly by the background harvesting task in main.py.
        """
        baselines: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

        with self._lock:
            for snap in self._snapshots:
                date_key = snap.recorded_at.date().isoformat()
                baselines[snap.student_id][date_key].append(snap.score)

        result: dict[str, dict[str, float]] = {}
        for student_id, days_data in baselines.items():
            result[student_id] = {
                day: round(sum(scores) / len(scores), 4)
                for day, scores in days_data.items()
            }

        with self._lock:
            self._baselines = result

        return result

    def get_baselines(self) -> dict[str, dict[str, float]]:
        with self._lock:
            return dict(self._baselines)

    # ── Feedback analytics ────────────────────────────────────────────────────

    def compute_feedback_metrics(self) -> dict[str, object]:
        """Compute precision/recall-style metrics from teacher feedback entries."""
        with self._lock:
            entries = list(self._feedback_log)

        if not entries:
            return {"total_feedback": 0, "accuracy": None, "improvement_note": None}

        correct = sum(
            1 for e in entries
            if e.predicted_state == e.confirmed_state
        )
        accuracy = round(correct / len(entries), 4)
        note = (
            "Model accuracy above 80% — predictions are reliable."
            if accuracy >= 0.8
            else "Accuracy below 80% — consider reviewing distracted/drowsy detection thresholds."
        )
        return {
            "total_feedback": len(entries),
            "correct_predictions": correct,
            "accuracy": accuracy,
            "improvement_note": note,
        }

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _derive_improvement_note(self) -> Optional[str]:
        with self._lock:
            entries = list(self._feedback_log)
        if not entries:
            return None
        correct = sum(1 for e in entries if e.predicted_state == e.confirmed_state)
        accuracy = correct / len(entries)
        if accuracy >= 0.8:
            return f"Self-assessment: {accuracy:.0%} prediction accuracy across {len(entries)} teacher feedback items — model performing well."
        return f"Self-assessment: {accuracy:.0%} accuracy ({len(entries)} items) — drowsy/distracted thresholds may need calibration."

    @staticmethod
    def _empty_insights() -> dict[str, object]:
        return {
            "session_id": None,
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "class_engagement_average": 0.0,
            "top_engaged_students": [],
            "disengagement_flags": [],
            "audio_visual_mismatches": [],
            "improvement_note": None,
        }
