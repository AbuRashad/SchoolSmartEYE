"""Unit 03: Path Tracking Unit — رصد الانتقالات المعتادة وكشف الانحرافات."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

import numpy as np

UNIT_03_NAME = "Path Tracking Unit"


@dataclass(frozen=True)
class PathObservation:
    track_id: str
    zone_sequence: tuple[str, ...]
    started_at: datetime
    ended_at: datetime
    is_anomalous: bool
    deviation_score: float  # [0,1]


class PathTrackingUnit:
    """Learns typical movement paths between zones and flags deviations."""

    def __init__(self, deviation_threshold: float = 0.65, min_observations: int = 5) -> None:
        if not (0 < deviation_threshold <= 1):
            raise ValueError("deviation_threshold must be in (0, 1]")
        if min_observations < 1:
            raise ValueError("min_observations must be >= 1")

        self.deviation_threshold = deviation_threshold
        self.min_observations = min_observations
        # transition_counts[(from_zone, to_zone)] = count
        self._transition_counts: dict[tuple[str, str], int] = defaultdict(int)
        self._total_transitions: int = 0

    def record_transition(self, from_zone: str, to_zone: str) -> None:
        self._transition_counts[(from_zone, to_zone)] += 1
        self._total_transitions += 1

    def transition_probability(self, from_zone: str, to_zone: str) -> float:
        if self._total_transitions == 0:
            return 0.0
        from_total = sum(
            v for (f, _), v in self._transition_counts.items() if f == from_zone
        )
        if from_total == 0:
            return 0.0
        return self._transition_counts[(from_zone, to_zone)] / from_total

    def evaluate_path(
        self,
        track_id: str,
        zone_sequence: list[str],
        started_at: datetime,
        ended_at: datetime,
    ) -> PathObservation:
        if len(zone_sequence) < 2:
            return PathObservation(
                track_id=track_id,
                zone_sequence=tuple(zone_sequence),
                started_at=started_at,
                ended_at=ended_at,
                is_anomalous=False,
                deviation_score=0.0,
            )

        if self._total_transitions < self.min_observations:
            return PathObservation(
                track_id=track_id,
                zone_sequence=tuple(zone_sequence),
                started_at=started_at,
                ended_at=ended_at,
                is_anomalous=False,
                deviation_score=0.0,
            )

        probs = []
        for i in range(len(zone_sequence) - 1):
            p = self.transition_probability(zone_sequence[i], zone_sequence[i + 1])
            probs.append(p)

        mean_prob = float(np.mean(probs)) if probs else 0.0
        deviation_score = float(np.clip(1.0 - mean_prob, 0.0, 1.0))
        is_anomalous = deviation_score >= self.deviation_threshold

        return PathObservation(
            track_id=track_id,
            zone_sequence=tuple(zone_sequence),
            started_at=started_at,
            ended_at=ended_at,
            is_anomalous=is_anomalous,
            deviation_score=deviation_score,
        )

    def most_common_transitions(self, top_k: int = 5) -> list[tuple[tuple[str, str], int]]:
        sorted_items = sorted(self._transition_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:top_k]
