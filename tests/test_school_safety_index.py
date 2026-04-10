import pytest

from datetime import datetime, timedelta

from app.services.crowd_density_forecasting import CrowdDensityForecaster, DensityObservation, DensityPrediction
from app.services.school_safety_index import (
    SSIWeights,
    compute_school_safety_index,
    compute_school_safety_index_with_forecast,
    predictive_risk_level_from_forecast,
)


def test_ssi_weighted_composite_returns_normalized_score() -> None:
    score = compute_school_safety_index(
        anomaly_coefficient=0.2,
        coherence_score=0.3,
        attendance_discrepancy=0.1,
        predictive_risk_level=0.4,
        weights=SSIWeights(w1=0.25, w2=0.25, w3=0.25, w4=0.25),
    )

    expected = (1.0 - (0.2 + 0.3 + 0.1 + 0.4) / 4.0) * 100.0
    assert score == pytest.approx(expected)
    assert 0.0 <= score <= 100.0


def test_ssi_auto_normalizes_weights() -> None:
    score = compute_school_safety_index(
        anomaly_coefficient=0.5,
        coherence_score=0.5,
        attendance_discrepancy=0.5,
        predictive_risk_level=0.5,
        weights=SSIWeights(w1=2.0, w2=2.0, w3=2.0, w4=2.0),
    )

    assert score == pytest.approx(50.0)


def test_ssi_clips_out_of_range_indicators() -> None:
    score = compute_school_safety_index(
        anomaly_coefficient=2.5,
        coherence_score=-1.0,
        attendance_discrepancy=0.0,
        predictive_risk_level=0.0,
        weights=SSIWeights(w1=1.0, w2=0.0, w3=0.0, w4=0.0),
    )

    # Risk is clipped to 1.0, so safety should be 0.
    assert score == pytest.approx(0.0)


def test_ssi_can_convert_raw_coherence_to_risk() -> None:
    score = compute_school_safety_index(
        anomaly_coefficient=0.2,
        coherence_score=0.9,
        attendance_discrepancy=0.1,
        predictive_risk_level=0.1,
        weights=SSIWeights(w1=0.25, w2=0.25, w3=0.25, w4=0.25),
        coherence_represents_alignment=True,
    )

    # coherence risk becomes (1 - 0.9) = 0.1
    expected = (1.0 - (0.2 + 0.1 + 0.1 + 0.1) / 4.0) * 100.0
    assert score == pytest.approx(expected)


def test_invalid_weights_raise() -> None:
    with pytest.raises(ValueError):
        compute_school_safety_index(
            anomaly_coefficient=0.1,
            coherence_score=0.2,
            attendance_discrepancy=0.3,
            predictive_risk_level=0.4,
            weights=SSIWeights(w1=0.0, w2=0.0, w3=0.0, w4=0.0),
        )


def test_predictive_risk_level_is_derived_from_density_forecast() -> None:
    prediction = DensityPrediction(
        location="School-Gate",
        forecast_time=datetime(2026, 4, 6, 15, 0),
        predicted_density=0.6,
        safety_threshold=0.75,
        risk_level="medium",
        warning=False,
        model_type="simulated_lstm",
    )

    risk = predictive_risk_level_from_forecast(prediction)

    assert risk == pytest.approx(0.8)


def test_ssi_can_be_computed_directly_from_density_forecaster() -> None:
    forecaster = CrowdDensityForecaster(safety_threshold=0.70)
    start = datetime(2026, 3, 30, 0, 0)
    history = []
    for week in range(3):
        monday = start + timedelta(days=7 * week)
        history.extend(
            [
                DensityObservation("School-Gate", monday.replace(hour=14, minute=45), 0.72),
                DensityObservation("School-Gate", monday.replace(hour=15, minute=0), 0.90),
                DensityObservation("School-Gate", monday.replace(hour=15, minute=15), 0.86),
            ]
        )

    forecaster.fit(history)
    score, prediction = compute_school_safety_index_with_forecast(
        anomaly_coefficient=0.2,
        coherence_score=0.25,
        attendance_discrepancy=0.1,
        forecaster=forecaster,
        location="School-Gate",
        current_time=datetime(2026, 4, 6, 14, 45),
        horizon_minutes=15,
        weights=SSIWeights(w1=0.25, w2=0.25, w3=0.20, w4=0.30),
    )

    assert prediction.warning is True
    assert prediction.predicted_density >= prediction.safety_threshold
    assert 0.0 <= score <= 100.0
    assert score < 70.0
