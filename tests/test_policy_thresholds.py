"""Tests for the policy threshold layer (stage 2)."""
import pytest

from app.core.policy_thresholds import (
    ATTENDANCE_REVIEW,
    CROWD_DENSITY_ELEVATED,
    NATIONAL_SSI_STANDARD,
    POLICY_VERSION,
    THRESHOLDS,
    THRESHOLDS_BY_LABEL,
    UPTIME_REVIEW,
    MetricThreshold,
    policy_metadata,
    threshold_for,
)
from app.services import specialist_agents


def test_labels_are_unique_and_registry_is_consistent():
    labels = [t.label for t in THRESHOLDS]
    assert len(labels) == len(set(labels))
    assert set(THRESHOLDS_BY_LABEL) == set(labels)


def test_policy_version_is_non_empty():
    assert POLICY_VERSION and isinstance(POLICY_VERSION, str)


def test_below_direction_breaches_on_lower_readings_only():
    assert ATTENDANCE_REVIEW.breached_by(89.9) is True
    assert ATTENDANCE_REVIEW.breached_by(90.0) is False
    assert ATTENDANCE_REVIEW.breached_by(95.0) is False


def test_above_direction_breaches_on_higher_readings_only():
    assert CROWD_DENSITY_ELEVATED.breached_by(0.80) is True
    assert CROWD_DENSITY_ELEVATED.breached_by(0.10) is False


def test_unknown_direction_is_rejected():
    bad = MetricThreshold(metric="x", value=1.0, direction="sideways",
                          label="bad", rationale="n/a")
    with pytest.raises(ValueError):
        bad.breached_by(5.0)


def test_describe_carries_value_direction_and_version():
    text = ATTENDANCE_REVIEW.describe(88.5)
    assert "attendance_rate=88.5" in text
    assert "below 90.0" in text
    assert POLICY_VERSION in text
    assert "attendance_review" in text


def test_threshold_for_raises_on_unknown_label():
    assert threshold_for("uptime_review") is UPTIME_REVIEW
    with pytest.raises(KeyError):
        threshold_for("does_not_exist")


def test_policy_metadata_is_serialisable_and_complete():
    meta = policy_metadata()
    assert meta["policy_version"] == POLICY_VERSION
    assert len(meta["thresholds"]) == len(THRESHOLDS)
    assert all({"metric", "value", "direction", "label", "rationale"} <= set(t)
               for t in meta["thresholds"])


def test_thresholds_are_immutable():
    with pytest.raises(Exception):
        ATTENDANCE_REVIEW.value = 50.0  # type: ignore[misc]


def test_national_ssi_standard_matches_report_generator_default():
    """The report generator default must come from this single source."""
    from app.services.report_generator import ReportGenerator
    assert ReportGenerator().national_standard_ssi == NATIONAL_SSI_STANDARD.value


# --- agents now emit threshold provenance -----------------------------------

def test_safety_agent_records_the_threshold_it_used():
    result = specialist_agents.safety_agent({"attendance_rate": 88.5})
    assert result["flags"]
    assert any("attendance_review" in ref for ref in result["threshold_refs"])
    assert any(POLICY_VERSION in ref for ref in result["threshold_refs"])
    assert result["policy_version"] == POLICY_VERSION


def test_safety_agent_records_no_threshold_when_within_policy():
    result = specialist_agents.safety_agent({"attendance_rate": 95.0, "incidents_today": 0})
    assert result["flags"] == []
    assert result["threshold_refs"] == []


def test_safety_crowd_threshold_still_triggers_at_0_75():
    """Preserves the original agent behaviour: 0.75 was, and remains, the trigger."""
    assert specialist_agents.safety_agent({"avg_crowd_density": 0.75})["flags"]
    assert specialist_agents.safety_agent({"avg_crowd_density": 0.74})["flags"] == []


def test_operations_agent_records_uptime_threshold():
    result = specialist_agents.operations_agent({"uptime_percent": 90.0})
    assert any("uptime_review" in ref for ref in result["threshold_refs"])


def test_operations_agent_now_flags_low_patrol_efficiency():
    """patrol_efficiency was collected but never reviewed; now it is."""
    result = specialist_agents.operations_agent({"patrol_efficiency": 50.0, "active_cameras": 3})
    assert any("patrol efficiency" in flag.lower() for flag in result["flags"])
    assert any("patrol_efficiency_review" in ref for ref in result["threshold_refs"])


def test_academic_agent_shares_the_attendance_threshold():
    """The safety and academic agents must not drift apart on attendance."""
    safety = specialist_agents.safety_agent({"attendance_rate": 89.0})
    academic = specialist_agents.academic_agent({"attendance_rate": 89.0})
    assert safety["flags"] and len(academic["recommendations"]) == 3


def test_agents_ignore_non_numeric_metric_values():
    result = specialist_agents.safety_agent({"attendance_rate": "low", "incidents_today": True})
    assert result["flags"] == []
    assert result["threshold_refs"] == []


def test_every_agent_reports_the_policy_version():
    metrics = {"attendance_rate": 88.0, "incidents_today": 1, "uptime_percent": 90.0}
    for agent in (specialist_agents.analytics_agent, specialist_agents.safety_agent,
                  specialist_agents.academic_agent, specialist_agents.operations_agent):
        assert agent(metrics)["policy_version"] == POLICY_VERSION
    assert specialist_agents.evidence_agent([])["policy_version"] == POLICY_VERSION
    assert specialist_agents.ethics_review_agent(metrics, [])["policy_version"] == POLICY_VERSION
