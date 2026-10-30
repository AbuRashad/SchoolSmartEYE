"""Explainable statistical learning primitives for school-level aggregate metrics.

This first iteration is intentionally not a predictive model. It establishes
minimum-history checks and robust baselines; callers must exclude demo data
from operational learning and must supply only approved aggregate values.
"""
from __future__ import annotations

import math
from statistics import median
from typing import Any

DEFAULT_MIN_HISTORY = 7
DEFAULT_MODIFIED_Z_THRESHOLD = 3.5


def assess_metric(
    metric: str,
    current_value: int | float,
    historical_values: list[int | float],
    *,
    min_history: int = DEFAULT_MIN_HISTORY,
    threshold: float = DEFAULT_MODIFIED_Z_THRESHOLD,
) -> dict[str, Any]:
    """Compare one current aggregate value with its historical robust baseline."""
    if not metric or len(metric) > 80:
        raise ValueError("metric must contain 1-80 characters")
    if min_history < 3:
        raise ValueError("min_history must be at least 3")
    if not math.isfinite(float(current_value)):
        raise ValueError("current_value must be finite")
    if not math.isfinite(float(threshold)) or threshold <= 0:
        raise ValueError("threshold must be a positive finite number")

    history: list[float] = []
    for value in historical_values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        numeric = float(value)
        if math.isfinite(numeric):
            history.append(numeric)

    if len(history) < min_history:
        return {
            "metric": metric,
            "status": "insufficient_history",
            "is_anomaly": False,
            "history_count": len(history),
            "required_history": min_history,
            "current_value": float(current_value),
            "baseline_median": None,
            "modified_z_score": None,
            "explanation": "Not enough valid historical observations to assess an anomaly.",
        }

    baseline = float(median(history))
    deviations = [abs(value - baseline) for value in history]
    mad = float(median(deviations))
    if mad == 0:
        differs = float(current_value) != baseline
        return {
            "metric": metric,
            "status": "constant_baseline_review" if differs else "within_baseline",
            "is_anomaly": False,
            "history_count": len(history),
            "required_history": min_history,
            "current_value": float(current_value),
            "baseline_median": baseline,
            "modified_z_score": None,
            "explanation": (
                "The historical baseline has zero median absolute deviation; "
                "the difference is surfaced for human review, not labelled an anomaly."
                if differs else "The current value matches the constant historical baseline."
            ),
        }

    modified_z = 0.6745 * (float(current_value) - baseline) / mad
    anomaly = abs(modified_z) >= threshold
    return {
        "metric": metric,
        "status": "anomaly_candidate" if anomaly else "within_baseline",
        "is_anomaly": anomaly,
        "history_count": len(history),
        "required_history": min_history,
        "current_value": float(current_value),
        "baseline_median": baseline,
        "modified_z_score": round(modified_z, 4),
        "explanation": (
            "The current aggregate value deviates materially from its historical median; "
            "verify data quality, seasonality and context before acting."
            if anomaly else "The current value is within the configured robust baseline."
        ),
    }
