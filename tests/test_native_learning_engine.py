from app.services.native_learning_engine import assess_metric


def test_insufficient_history_does_not_flag_anomaly():
    result = assess_metric("attendance_rate", 40, [90, 91, 92])
    assert result["status"] == "insufficient_history"
    assert result["is_anomaly"] is False


def test_robust_baseline_detects_large_deviation():
    result = assess_metric("attendance_rate", 40, [94, 95, 95, 96, 94, 95, 96])
    assert result["status"] == "anomaly_candidate"
    assert result["is_anomaly"] is True
    assert result["baseline_median"] == 95


def test_constant_baseline_requires_human_review_not_anomaly():
    result = assess_metric("uptime_percent", 80, [99, 99, 99, 99, 99, 99, 99])
    assert result["status"] == "constant_baseline_review"
    assert result["is_anomaly"] is False


def test_non_finite_history_is_ignored():
    result = assess_metric("metric", 10, [1, 1, 1, 1, 1, 1, float("nan")])
    assert result["history_count"] == 6
    assert result["status"] == "insufficient_history"


def test_invalid_current_value_is_rejected():
    try:
        assess_metric("metric", float("inf"), [1, 2, 3, 4, 5, 6, 7])
    except ValueError:
        pass
    else:
        raise AssertionError("non-finite current values must be rejected")
