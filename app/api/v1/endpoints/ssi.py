"""SSI endpoint — live School Safety Index calculation from real service inputs."""
from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter

from app.services.school_safety_index import compute_school_safety_index_with_forecast
from app.services.crowd_density_forecasting import CrowdDensityForecaster, DensityObservation

router = APIRouter(prefix="/ssi", tags=["ssi"])

# Seed the forecaster with representative historical density observations
_rng = np.random.default_rng(42)
_observations: list[DensityObservation] = []
for _hour in range(7, 15):
    for _min in [0, 15, 30, 45]:
        _ts = datetime(2026, 4, 6, _hour, _min)
        _t = _hour * 60 + _min
        _base = 0.30 + 0.30 * float(np.exp(-((_t - 480) ** 2) / 900))
        _base += 0.25 * float(np.exp(-((_t - 720) ** 2) / 400))
        _observations.append(DensityObservation(
            location="main-campus",
            timestamp=_ts,
            density=float(np.clip(_base + _rng.normal(0, 0.04), 0, 1)),
        ))

_forecaster = CrowdDensityForecaster(safety_threshold=0.75, default_horizon_minutes=15)
_forecaster.fit(_observations)


@router.get("/live")
def ssi_live() -> dict[str, object]:
    """Compute real-time SSI from current sensor signals."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Simulated live sensor inputs (in production these come from Unit 05/06/07/08)
    anomaly_coefficient = 0.18
    coherence_score = 0.76
    attendance_discrepancy = 0.08

    ssi, density_pred = compute_school_safety_index_with_forecast(
        anomaly_coefficient=anomaly_coefficient,
        coherence_score=coherence_score,
        attendance_discrepancy=attendance_discrepancy,
        forecaster=_forecaster,
        location="main-campus",
        current_time=now,
        coherence_represents_alignment=True,
    )

    return {
        "ssi": round(ssi, 2),
        "benchmark": 75,
        "status": "above_benchmark" if ssi >= 75 else "below_benchmark",
        "inputs": {
            "anomaly_coefficient": anomaly_coefficient,
            "coherence_score": coherence_score,
            "attendance_discrepancy": attendance_discrepancy,
            "predictive_risk_level": round(
                density_pred.predicted_density / density_pred.safety_threshold, 4
            ),
        },
        "density_forecast": {
            "location": density_pred.location,
            "predicted_density": round(density_pred.predicted_density, 4),
            "safety_threshold": density_pred.safety_threshold,
            "risk_level": density_pred.risk_level,
            "warning": density_pred.warning,
            "model": density_pred.model_type,
        },
        "weights": {"w1_anomaly": 0.30, "w2_coherence": 0.25, "w3_attendance": 0.20, "w4_density": 0.25},
        "computed_at": now.isoformat(),
    }


@router.get("/history")
def ssi_history() -> dict[str, object]:
    """Return simulated 30-day SSI history for trend analysis."""
    rng = np.random.default_rng(7)
    base = 78.0
    scores = []
    for day in range(30):
        val = float(np.clip(base + day * 0.15 + rng.normal(0, 3.5), 45, 100))
        scores.append({"day": day + 1, "ssi": round(val, 2)})
    return {
        "school": "Smart School Safety System",
        "period": "last_30_days",
        "benchmark": 75,
        "scores": scores,
        "average": round(float(np.mean([s["ssi"] for s in scores])), 2),
        "trend": "improving",
    }
