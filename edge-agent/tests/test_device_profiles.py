import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).parents[1] / "device_profiles.py"
SPEC = importlib.util.spec_from_file_location("device_profiles", MODULE_PATH)
profiles = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(profiles)


def candidate():
    return {
        "profile_id": "vendor-model-revA-fw1",
        "manufacturer": "Example manufacturer",
        "model_name": "Example model",
        "firmware_version": "1.0",
        "transport": "ble",
        "sensors": ["heart_rate", "movement_activity"],
        "verification_status": "pending",
        "evidence": [{"type": "vendor_datasheet", "reference": "internal-review"}],
    }


class DeviceProfileTests(unittest.TestCase):
    def test_registry_waits_for_model_selection(self):
        registry = profiles.load_registry()
        self.assertEqual(registry["status"], "awaiting_hardware_selection")
        self.assertEqual(registry["profiles"], [])

    def test_valid_candidate(self):
        self.assertEqual(profiles.validate_profile(candidate())["transport"], "ble")

    def test_rejects_unconfirmed_transport(self):
        item = candidate()
        item["transport"] = "maybe-bluetooth"
        with self.assertRaisesRegex(ValueError, "transport"):
            profiles.validate_profile(item)

    def test_rejects_unknown_capability(self):
        item = candidate()
        item["sensors"].append("emotion")
        with self.assertRaisesRegex(ValueError, "sensor"):
            profiles.validate_profile(item)

    def test_pilot_verified_requires_test_evidence(self):
        item = candidate()
        item["verification_status"] = "pilot_verified"
        with self.assertRaisesRegex(ValueError, "supervised"):
            profiles.validate_profile(item)

    def test_sampling_interval_must_be_positive(self):
        item = candidate()
        item["sampling_interval_seconds"] = 0
        with self.assertRaisesRegex(ValueError, "positive"):
            profiles.validate_profile(item)


if __name__ == "__main__":
    unittest.main()
