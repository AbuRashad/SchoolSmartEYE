from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np

from app.services.crowd_density_forecasting import CrowdDensityForecaster, DensityPrediction


@dataclass(frozen=True)
class SSIWeights:
    w1: float = 0.30
    w2: float = 0.25
    w3: float = 0.20
    w4: float = 0.25

    def normalized(self) -> np.ndarray:
        values = np.array([self.w1, self.w2, self.w3, self.w4], dtype=np.float64)
        if np.any(values < 0):
            raise ValueError("SSI weights must be non-negative")

        total = float(np.sum(values))
        if total <= 0:
            raise ValueError("At least one SSI weight must be greater than zero")
        return values / total


def compute_school_safety_index(
    anomaly_coefficient: float,
    coherence_score: float,
    attendance_discrepancy: float,
    predictive_risk_level: float,
    weights: SSIWeights | None = None,
    coherence_represents_alignment: bool = False,
) -> float:
    """Compute School Safety Index (SSI) as normalized weighted composite.

    Args:
        anomaly_coefficient: SBM anomaly in [0, 1] where higher is riskier.
        coherence_score: CBC score in [0, 1]. If this is raw coherence
            (higher is safer), set coherence_represents_alignment=True.
        attendance_discrepancy: Attendance discrepancy in [0, 1], higher is riskier.
        predictive_risk_level: Forecasted density risk in [0, 1], higher is riskier.
        weights: Weights for W1..W4. Weights are auto-normalized.
        coherence_represents_alignment: Convert coherence into risk using
            (1 - coherence_score) when True.

    Returns:
        SSI score in [0, 100], where higher means higher institutional safety.
    """
        
    weights = weights or SSIWeights()
    normalized_weights = weights.normalized()

    indicators = np.array(
        [
            anomaly_coefficient,
            coherence_score,
            attendance_discrepancy,
            predictive_risk_level,
        ],
        dtype=np.float64,
    )
    if not np.all(np.isfinite(indicators)):
        raise ValueError("All SSI indicators must be finite numeric values")

    indicators = np.clip(indicators, 0.0, 1.0)
    if coherence_represents_alignment:
        indicators[1] = 1.0 - indicators[1]

    weighted_risk = float(np.dot(normalized_weights, indicators))
    safety_score = (1.0 - weighted_risk) * 100.0
    return float(np.clip(safety_score, 0.0, 100.0))


def predictive_risk_level_from_forecast(density_prediction: DensityPrediction) -> float:
    """Convert a density forecast into normalized SSI risk term W4 in [0, 1]."""
    if density_prediction.safety_threshold <= 0:
        raise ValueError("density_prediction.safety_threshold must be greater than zero")

    risk = density_prediction.predicted_density / density_prediction.safety_threshold
    return float(np.clip(risk, 0.0, 1.0))


def compute_school_safety_index_with_forecast(
    anomaly_coefficient: float,
    coherence_score: float,
    attendance_discrepancy: float,
    forecaster: CrowdDensityForecaster,
    location: str,
    current_time: datetime,
    horizon_minutes: int | None = None,
    weights: SSIWeights | None = None,
    coherence_represents_alignment: bool = False,
) -> tuple[float, DensityPrediction]:
    """Compute SSI using the density forecaster directly for the W4 input."""
    density_prediction = forecaster.predict(
        location=location,
        current_time=current_time,
        horizon_minutes=horizon_minutes,
    )
    predictive_risk_level = predictive_risk_level_from_forecast(density_prediction)
    score = compute_school_safety_index(
        anomaly_coefficient=anomaly_coefficient,
        coherence_score=coherence_score,
        attendance_discrepancy=attendance_discrepancy,
        predictive_risk_level=predictive_risk_level,
        weights=weights,
        coherence_represents_alignment=coherence_represents_alignment,
    )
    return score, density_prediction
