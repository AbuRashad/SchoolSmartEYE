"""Version-controlled WAI hardware capability registry."""
from __future__ import annotations

import json
from pathlib import Path

ALLOWED_TRANSPORTS = {"ble", "wifi", "lora", "usb", "ethernet", "other"}
ALLOWED_SENSORS = {"heart_rate", "hrv", "skin_temperature", "movement_activity", "eda"}
ALLOWED_VERIFICATION = {"pending", "specification_reviewed", "pilot_verified"}


def validate_profile(profile: dict) -> dict:
    required = {"profile_id", "manufacturer", "model_name", "firmware_version",
                "transport", "sensors", "verification_status", "evidence"}
    optional = {"hardware_revision", "sampling_interval_seconds", "calibration_method", "notes"}
    missing = required - set(profile)
    unknown = set(profile) - required - optional
    if missing:
        raise ValueError(f"Missing fields: {', '.join(sorted(missing))}")
    if unknown:
        raise ValueError(f"Unknown fields: {', '.join(sorted(unknown))}")
    for field in ("profile_id", "manufacturer", "model_name", "firmware_version"):
        if not isinstance(profile[field], str) or not profile[field].strip():
            raise ValueError(f"{field} must be a non-empty string")
    if profile["transport"] not in ALLOWED_TRANSPORTS:
        raise ValueError("Unsupported transport")
    sensors = profile["sensors"]
    if not isinstance(sensors, list) or not sensors or len(sensors) != len(set(sensors)):
        raise ValueError("sensors must be a non-empty unique list")
    if set(sensors) - ALLOWED_SENSORS:
        raise ValueError("Unsupported sensor capability")
    if profile["verification_status"] not in ALLOWED_VERIFICATION:
        raise ValueError("Invalid verification status")
    evidence = profile["evidence"]
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("Evidence references are required")
    if profile["verification_status"] == "pilot_verified" and not any(
        isinstance(item, dict) and item.get("type") == "supervised_hardware_test"
        for item in evidence
    ):
        raise ValueError("pilot_verified requires supervised hardware test evidence")
    interval = profile.get("sampling_interval_seconds")
    if interval is not None and (
        isinstance(interval, bool) or not isinstance(interval, (int, float)) or interval <= 0
    ):
        raise ValueError("Sampling interval must be positive")
    return dict(profile)


def load_registry(path: Path | None = None) -> dict:
    registry_path = path or Path(__file__).with_name("device_profiles.json")
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    if data.get("registry_version") != "1" or not isinstance(data.get("profiles"), list):
        raise ValueError("Unsupported or malformed registry")
    seen = set()
    for profile in data["profiles"]:
        validate_profile(profile)
        if profile["profile_id"] in seen:
            raise ValueError("Duplicate profile_id")
        seen.add(profile["profile_id"])
    return data
