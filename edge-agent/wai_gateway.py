"""Transport-neutral WAI edge gateway scaffold.

This module validates locally prepared observations only. It deliberately does
not transmit data: a physical transport and hardware profile must be verified
before an adapter is implemented.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

SCHEMA_VERSION = "wai.v1"
MEASUREMENTS = {
    "heart_rate_bpm": (30.0, 240.0),
    "hrv_ms": (0.0, 500.0),
    "skin_temperature_c": (20.0, 45.0),
    "movement_activity_score": (0.0, 100.0),
    "eda_us": (0.0, 100.0),
}
ALLOWED_FIELDS = {
    "schema_version", "observed_at", *MEASUREMENTS.keys(),
    "battery_level", "idempotency_key",
}


@runtime_checkable
class TransportAdapter(Protocol):
    """Future BLE/Wi-Fi/LoRa adapter contract; no transport is selected yet."""

    def receive_observation(self) -> dict:
        """Return one decoded, typed observation from a verified device."""
        ...


def validate_observation(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Observation must be a JSON object")
    unknown = set(payload) - ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"Unsupported fields: {', '.join(sorted(unknown))}")
    if payload.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        raise ValueError("Unsupported schema_version")
    timestamp = payload.get("observed_at")
    if not isinstance(timestamp, str):
        raise ValueError("observed_at must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("observed_at must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("observed_at must include a timezone")

    present = 0
    for name, (minimum, maximum) in MEASUREMENTS.items():
        value = payload.get(name)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be numeric")
        if not math.isfinite(value) or not minimum <= value <= maximum:
            raise ValueError(f"{name} is outside the documented wai.v1 range")
        present += 1
    if present == 0:
        raise ValueError("At least one measurement field is required")

    battery = payload.get("battery_level")
    if battery is not None and (
        isinstance(battery, bool) or not isinstance(battery, int) or not 0 <= battery <= 100
    ):
        raise ValueError("battery_level must be an integer from 0 to 100")
    key = payload.get("idempotency_key")
    if not isinstance(key, str) or not 8 <= len(key) <= 128:
        raise ValueError("idempotency_key must contain 8 to 128 characters")

    normalized = dict(payload)
    normalized.setdefault("schema_version", SCHEMA_VERSION)
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="WAI local validation-only gateway")
    parser.add_argument("--validate-only", action="store_true", help="validate JSON locally; never transmit")
    parser.add_argument("--input", type=Path, required=True, help="path to one JSON observation")
    args = parser.parse_args()
    if not args.validate_only:
        parser.error("Only --validate-only is available until hardware and transport are verified")
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        validated = validate_observation(payload)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"VALIDATION_FAILED: {exc}", file=sys.stderr)
        return 2

    # Do not print measurements, identifiers, credentials, or student data.
    print(json.dumps({
        "result": "valid",
        "mode": "validation_only",
        "schema_version": validated["schema_version"],
        "transmission": "disabled",
        "hardware_status": "not_selected",
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
