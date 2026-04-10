from datetime import datetime, timedelta

from app.services.crowd_density_forecasting import CrowdDensityForecaster, DensityObservation


def _build_history() -> list[DensityObservation]:
    base_day = datetime(2026, 3, 30, 0, 0)
    observations: list[DensityObservation] = []

    for week in range(3):
        monday = base_day + timedelta(days=7 * week)

        observations.extend(
            [
                DensityObservation("Classroom-A", monday.replace(hour=9, minute=0), 0.18),
                DensityObservation("Classroom-A", monday.replace(hour=9, minute=15), 0.22),
                DensityObservation("Classroom-A", monday.replace(hour=9, minute=30), 0.20),
                DensityObservation("School-Gate", monday.replace(hour=14, minute=45), 0.72),
                DensityObservation("School-Gate", monday.replace(hour=15, minute=0), 0.92),
                DensityObservation("School-Gate", monday.replace(hour=15, minute=15), 0.88),
            ]
        )

    return observations


def test_normal_pattern_predicts_low_density_during_lesson_time() -> None:
    forecaster = CrowdDensityForecaster(safety_threshold=0.75)
    forecaster.fit(_build_history())

    prediction = forecaster.predict(
        location="Classroom-A",
        current_time=datetime(2026, 4, 6, 8, 50),
        horizon_minutes=15,
    )

    assert prediction.predicted_density < 0.4
    assert prediction.risk_level == "low"
    assert prediction.warning is False


def test_peak_prediction_identifies_high_density_at_gate_during_dismissal() -> None:
    forecaster = CrowdDensityForecaster(safety_threshold=0.75)
    forecaster.fit(_build_history())

    prediction = forecaster.predict(
        location="School-Gate",
        current_time=datetime(2026, 4, 6, 14, 45),
        horizon_minutes=15,
    )

    assert prediction.predicted_density >= 0.75
    assert prediction.risk_level == "high"
    assert prediction.warning is True


def test_proactive_alert_triggers_before_high_density_event_occurs() -> None:
    forecaster = CrowdDensityForecaster(safety_threshold=0.70, default_horizon_minutes=30)
    forecaster.fit(_build_history())

    prediction = forecaster.predict(
        location="School-Gate",
        current_time=datetime(2026, 4, 6, 14, 30),
        horizon_minutes=30,
    )

    assert prediction.forecast_time == datetime(2026, 4, 6, 15, 0)
    assert prediction.predicted_density >= prediction.safety_threshold
    assert prediction.warning is True
