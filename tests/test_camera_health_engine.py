from datetime import datetime, timezone

import pytest

from app.services.camera_health_engine import (
    CameraHealthMetrics,
    CameraHealthStatus,
    classify_camera_health,
    simulate_camera_health,
)


NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("scenario", "expected"),
    [
        ("online", CameraHealthStatus.ONLINE),
        ("degraded", CameraHealthStatus.DEGRADED),
        ("offline", CameraHealthStatus.OFFLINE),
        ("stalled", CameraHealthStatus.STALLED),
    ],
)
def test_synthetic_scenarios_have_expected_status(scenario, expected):
    results = list(simulate_camera_health("cam-test", scenario, start_at=NOW))
    assert len(results) == 6
    assert {item.status for item in results} == {expected}


def test_reconnecting_scenario_transitions_from_offline_to_online():
    results = list(simulate_camera_health("cam-test", "reconnecting", start_at=NOW))
    assert all(item.status == CameraHealthStatus.OFFLINE for item in results[:-1])
    assert results[-1].status == CameraHealthStatus.ONLINE
    assert results[-1].reconnect_count == 1


def test_frozen_frame_is_stalled_when_heartbeat_is_fresh():
    metrics = CameraHealthMetrics(
        camera_id="cam-freeze",
        observed_at=NOW,
        last_seen_age_seconds=1,
        fps=0,
        latency_ms=90,
        frozen_frame=True,
    )
    assert classify_camera_health(metrics).status == CameraHealthStatus.STALLED


def test_offline_threshold_takes_precedence_over_stalled():
    metrics = CameraHealthMetrics(
        camera_id="cam-offline",
        observed_at=NOW,
        last_seen_age_seconds=60,
        fps=0,
        latency_ms=0,
        consecutive_missed_heartbeats=4,
        frozen_frame=True,
    )
    assert classify_camera_health(metrics).status == CameraHealthStatus.OFFLINE


@pytest.mark.parametrize(
    "kwargs",
    [
        {"last_seen_age_seconds": -1},
        {"fps": -1},
        {"latency_ms": -1},
        {"consecutive_missed_heartbeats": -1},
        {"reconnect_count": -1},
    ],
)
def test_invalid_metrics_are_rejected(kwargs):
    values = dict(
        camera_id="cam-test",
        observed_at=NOW,
        last_seen_age_seconds=1,
        fps=20,
        latency_ms=50,
        consecutive_missed_heartbeats=0,
        reconnect_count=0,
        frozen_frame=False,
    )
    values.update(kwargs)
    with pytest.raises(ValueError):
        CameraHealthMetrics(**values)


def test_simulator_requires_timezone_aware_start():
    with pytest.raises(ValueError):
        list(simulate_camera_health("cam-test", "online", start_at=datetime(2026, 10, 30)))
