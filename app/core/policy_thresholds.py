"""Single source of truth for SchoolSmartEYE review thresholds.

Thresholds were previously hardcoded at their point of use (specialist agents,
report generator), so a policy change required editing several files and could
not be traced afterwards. Every decision now carries the threshold it used and
the policy version it came from.

This module holds *values and provenance only*. It must not import the agents or
the orchestrator, or the dependency would become circular.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

# Bump when any threshold below changes, so historical findings stay auditable.
POLICY_VERSION = "2026.10-v1"


@dataclass(frozen=True)
class MetricThreshold:
    """A review threshold for one aggregate metric.

    `direction` records which side of the threshold warrants review, so a
    consumer never has to guess whether a high or low reading is the concern.
    """

    metric: str
    value: float
    direction: str  # "below" | "above"
    label: str
    rationale: str

    def breached_by(self, reading: int | float) -> bool:
        """Return True when this reading crosses the review threshold."""
        if self.direction == "below":
            return reading < self.value
        if self.direction == "above":
            return reading > self.value
        raise ValueError(f"unsupported threshold direction: {self.direction!r}")

    def describe(self, reading: int | float) -> str:
        """Human-readable provenance for a decision made against this threshold."""
        return (
            f"{self.metric}={reading} {self.direction} {self.value} "
            f"[{self.label}, policy {POLICY_VERSION}]"
        )


# Attendance below this level warrants review.
ATTENDANCE_REVIEW = MetricThreshold(
    metric="attendance_rate", value=90.0, direction="below",
    label="attendance_review",
    rationale="School-wide attendance below 90% warrants context review.",
)

# Incident count above this level warrants review. Zero incidents is not a breach.
INCIDENTS_TODAY_REVIEW = MetricThreshold(
    metric="incidents_today", value=0.0, direction="above",
    label="incidents_today_review",
    rationale="Any reported incident warrants checking the source reports.",
)

INCIDENTS_WEEK_REVIEW = MetricThreshold(
    metric="incidents_week", value=0.0, direction="above",
    label="incidents_week_review",
    rationale="Any reported incident in the week warrants checking the source reports.",
)

# Crowd density at or above this level is treated as elevated (normalised 0..1).
CROWD_DENSITY_ELEVATED = MetricThreshold(
    metric="avg_crowd_density", value=0.75, direction="above",
    label="crowd_density_elevated",
    rationale="Crowd density at or above 0.75 in normalised units is elevated.",
)

# System uptime below this level warrants a health check.
UPTIME_REVIEW = MetricThreshold(
    metric="uptime_percent", value=99.0, direction="below",
    label="uptime_review",
    rationale="Uptime below 99% indicates a service-health concern.",
)

# Patrol efficiency below this level warrants review.
PATROL_EFFICIENCY_REVIEW = MetricThreshold(
    metric="patrol_efficiency", value=75.0, direction="below",
    label="patrol_efficiency_review",
    rationale="Patrol efficiency below 75% warrants an operational review.",
)

# Institution-level SSI used as the national benchmark in ministry reporting.
NATIONAL_SSI_STANDARD = MetricThreshold(
    metric="ssi", value=75.0, direction="below",
    label="national_ssi_standard",
    rationale="National SSI benchmark for institutional self-assessment.",
)

# Ordered registry: the canonical list consumers iterate over.
THRESHOLDS: tuple[MetricThreshold, ...] = (
    ATTENDANCE_REVIEW,
    INCIDENTS_TODAY_REVIEW,
    INCIDENTS_WEEK_REVIEW,
    CROWD_DENSITY_ELEVATED,
    UPTIME_REVIEW,
    PATROL_EFFICIENCY_REVIEW,
    NATIONAL_SSI_STANDARD,
)

THRESHOLDS_BY_LABEL: dict[str, MetricThreshold] = {t.label: t for t in THRESHOLDS}


def policy_metadata() -> dict[str, Any]:
    """Policy version plus every threshold, for embedding in a response payload."""
    return {
        "policy_version": POLICY_VERSION,
        "thresholds": [asdict(t) for t in THRESHOLDS],
    }


def threshold_for(label: str) -> MetricThreshold:
    """Look a threshold up by label; raises KeyError for an unknown label."""
    return THRESHOLDS_BY_LABEL[label]
