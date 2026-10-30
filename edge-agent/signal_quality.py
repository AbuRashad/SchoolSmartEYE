"""Local WAI signal-quality assessment; no transmission or clinical interpretation."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from wai_gateway import MEASUREMENTS, validate_observation

SENSOR_TO_FIELDS = {
    "heart_rate": {"heart_rate_bpm"},
    "hrv": {"hrv_ms"},
    "skin_temperature": {"skin_temperature_c"},
    "movement_activity": {"movement_activity_score"},
    "eda": {"eda_us"},
}
ALLOWED_MODES = {"demo", "live_unverified"}


def _parse_time(value: str | datetime, field: str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{field} must be a valid ISO-8601 timestamp") from exc
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(timezone.utc)


def assess_signal_quality(
    payload: dict,
    profile: dict,
    *,
    received_at: str | datetime,
    data_mode: str,
    previous_observed_at: str | datetime | None = None,
    seen_idempotency_keys: Iterable[str] = (),
    max_age_seconds: int = 300,
) -> dict:
    """Return metadata-only quality flags. Caller owns persistence and access control.

    Demo records are explicitly non-live and must never count toward school
    reporting coverage. This function never transmits or logs sensor values.
    """
    if data_mode not in ALLOWED_MODES:
        raise ValueError("data_mode must be explicitly demo or live_unverified")
    if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, int) or max_age_seconds < 0:
        raise ValueError("max_age_seconds must be a non-negative integer")

    flags: list[str] = []
    try:
        normalized = validate_observation(payload)
    except ValueError as exc:
        message = str(exc)
        flags.append("out_of_range" if "outside the documented" in message else "invalid_observation")
        return {
            "quality_status": "rejected",
            "flags": flags,
            "data_mode": data_mode,
            "eligible_for_live_coverage": False,
            "human_review_required": True,
        }

    allowed_fields = set()
    for sensor in profile.get("sensors", []):
        allowed_fields.update(SENSOR_TO_FIELDS.get(sensor, set()))
    present_fields = {name for name in MEASUREMENTS if normalized.get(name) is not None}
    if not present_fields:
        flags.append("incomplete")
    if present_fields - allowed_fields:
        flags.append("unsupported_by_profile")

    observed = _parse_time(normalized["observed_at"], "observed_at")
    received = _parse_time(received_at, "received_at")
    age = (received - observed).total_seconds()
    if age > max_age_seconds:
        flags.append("stale")
    elif age < -max_age_seconds:
        flags.append("future_timestamp")

    key = normalized["idempotency_key"]
    if key in set(seen_idempotency_keys):
        flags.append("duplicate")

    interval = profile.get("sampling_interval_seconds")
    if previous_observed_at is not None and interval is not None:
        previous = _parse_time(previous_observed_at, "previous_observed_at")
        elapsed = (observed - previous).total_seconds()
        if elapsed > float(interval) * 1.5:
            flags.append("gap_detected")

    if data_mode == "demo":
        flags.append("demo_data")
    blocking = {"out_of_range", "invalid_observation", "unsupported_by_profile",
                "stale", "future_timestamp", "duplicate", "incomplete"}
    blocked = bool(blocking.intersection(flags))
    return {
        "quality_status": "review_required" if blocked or "gap_detected" in flags or data_mode == "demo" else "accepted_unverified",
        "flags": flags or ["no_quality_issue_detected"],
        "data_mode": data_mode,
        "eligible_for_live_coverage": data_mode == "live_unverified" and not blocked,
        "human_review_required": True,
    }
