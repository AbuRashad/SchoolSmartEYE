import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).parents[1] / "wai_gateway.py"
SPEC = importlib.util.spec_from_file_location("wai_gateway", MODULE_PATH)
gateway = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gateway)


def sample():
    return {
        "schema_version": "wai.v1",
        "observed_at": "2026-10-30T08:30:00+02:00",
        "heart_rate_bpm": 82,
        "idempotency_key": "event-0000001",
    }


class WAIValidationTests(unittest.TestCase):
    def test_valid_observation(self):
        result = gateway.validate_observation(sample())
        self.assertEqual(result["schema_version"], "wai.v1")

    def test_rejects_naive_timestamp(self):
        payload = sample()
        payload["observed_at"] = "2026-10-30T08:30:00"
        with self.assertRaisesRegex(ValueError, "timezone"):
            gateway.validate_observation(payload)

    def test_rejects_out_of_range_measurement(self):
        payload = sample()
        payload["heart_rate_bpm"] = 500
        with self.assertRaisesRegex(ValueError, "range"):
            gateway.validate_observation(payload)

    def test_rejects_unknown_fields(self):
        payload = sample()
        payload["student_id"] = "must-not-be-supplied"
        with self.assertRaisesRegex(ValueError, "Unsupported fields"):
            gateway.validate_observation(payload)

    def test_battery_alone_is_not_an_observation(self):
        payload = sample()
        payload.pop("heart_rate_bpm")
        payload["battery_level"] = 90
        with self.assertRaisesRegex(ValueError, "At least one"):
            gateway.validate_observation(payload)

    def test_rejects_non_finite_measurement(self):
        payload = sample()
        payload["heart_rate_bpm"] = float("nan")
        with self.assertRaisesRegex(ValueError, "range"):
            gateway.validate_observation(payload)


if __name__ == "__main__":
    unittest.main()
