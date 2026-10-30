import importlib.util
from pathlib import Path
import sys
import unittest

EDGE_DIR = Path(__file__).parents[1]
sys.path.insert(0, str(EDGE_DIR))
SPEC = importlib.util.spec_from_file_location("signal_quality", EDGE_DIR / "signal_quality.py")
quality = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(quality)


def observation(**overrides):
    value = {
        "schema_version": "wai.v1",
        "observed_at": "2026-10-30T10:00:00+00:00",
        "heart_rate_bpm": 82,
        "idempotency_key": "sample-key-0001",
    }
    value.update(overrides)
    return value


def profile(**overrides):
    value = {
        "profile_id": "candidate-a",
        "sensors": ["heart_rate"],
        "sampling_interval_seconds": 60,
    }
    value.update(overrides)
    return value


class SignalQualityTests(unittest.TestCase):
    def assess(self, payload=None, **kwargs):
        received_at = kwargs.pop("received_at", "2026-10-30T10:00:30+00:00")
        return quality.assess_signal_quality(
            payload or observation(), profile(),
            received_at=received_at, data_mode="live_unverified", **kwargs
        )

    def test_clean_observation_is_unverified_and_coverage_eligible(self):
        result = self.assess()
        self.assertEqual(result["quality_status"], "accepted_unverified")
        self.assertTrue(result["eligible_for_live_coverage"])
        self.assertTrue(result["human_review_required"])

    def test_demo_never_counts_toward_live_coverage(self):
        result = quality.assess_signal_quality(
            observation(), profile(),
            received_at="2026-10-30T10:00:30+00:00", data_mode="demo"
        )
        self.assertIn("demo_data", result["flags"])
        self.assertFalse(result["eligible_for_live_coverage"])

    def test_rejects_sensor_not_supported_by_selected_profile(self):
        result = self.assess(observation(hrv_ms=45))
        self.assertIn("unsupported_by_profile", result["flags"])
        self.assertFalse(result["eligible_for_live_coverage"])

    def test_marks_stale_observation(self):
        result = self.assess(received_at="2026-10-30T10:10:00+00:00")
        self.assertIn("stale", result["flags"])

    def test_marks_duplicate_idempotency_key(self):
        result = self.assess(seen_idempotency_keys=["sample-key-0001"])
        self.assertIn("duplicate", result["flags"])
        self.assertFalse(result["eligible_for_live_coverage"])

    def test_detects_gap_only_when_profile_has_sampling_interval(self):
        result = self.assess(previous_observed_at="2026-10-30T09:57:00+00:00")
        self.assertIn("gap_detected", result["flags"])
        self.assertFalse(result["eligible_for_live_coverage"])

    def test_out_of_range_is_rejected_without_echoing_measurement(self):
        result = self.assess(observation(heart_rate_bpm=999))
        self.assertEqual(result["quality_status"], "rejected")
        self.assertIn("out_of_range", result["flags"])
        self.assertNotIn("999", str(result))

    def test_data_mode_must_be_explicit_and_valid(self):
        with self.assertRaisesRegex(ValueError, "data_mode"):
            quality.assess_signal_quality(
                observation(), profile(),
                received_at="2026-10-30T10:00:30+00:00", data_mode="unknown"
            )


if __name__ == "__main__":
    unittest.main()
