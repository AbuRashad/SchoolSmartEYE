# WAI Wearable Device Integration Protocol

Status: integration contract for the current SchoolSmartEYE API. This is not a claim that a specific wristband firmware has been tested.

## Device lifecycle

1. A school principal authenticates to SchoolSmartEYE.
2. The principal provisions one active credential for an active bracelet:
   `POST /api/v1/wearables/devices/{bracelet_id}`
3. The API returns `device_id` and `device_secret` once. Store the secret in the gateway/device secret store. Never commit it, print it to logs, or put it in a browser.
4. The device sends observations to:
   `POST /api/v1/wearables/edge/{device_id}`
5. A principal can revoke the credential:
   `POST /api/v1/wearables/devices/{device_id}/revoke`

Use HTTPS for all non-local deployments. The edge credential is sent only in the `X-Wearable-Device-Secret` header.

## Current observation schema

The accepted schema version is `wai.v1`. Unknown fields are rejected.

Illustrative payload (synthetic values for protocol documentation only):

```json
{
  "schema_version": "wai.v1",
  "observed_at": "2026-10-30T08:30:00+02:00",
  "heart_rate_bpm": 82.0,
  "hrv_ms": 46.5,
  "skin_temperature_c": 33.2,
  "movement_activity_score": 28.0,
  "eda_us": null,
  "battery_level": 91,
  "idempotency_key": "device-generated-unique-event-id"
}
```

| Field | Unit / range | Required |
|---|---|---|
| `schema_version` | `wai.v1` | No (defaults to wai.v1) |
| `observed_at` | ISO-8601 timestamp with timezone | Yes |
| `heart_rate_bpm` | 30–240 bpm | One measurement required |
| `hrv_ms` | 0–500 ms | Optional |
| `skin_temperature_c` | 20–45 °C | Optional |
| `movement_activity_score` | 0–100; device-defined scale must be documented | Optional |
| `eda_us` | 0–100 µS; optional sensor | Optional |
| `battery_level` | 0–100% | Optional |
| `idempotency_key` | 8–128 characters, unique per device event | Yes |

At least one of the five physiological/activity measurement fields is required. Battery alone is not an observation.

## Validation and delivery rules

- Source timestamps must include a timezone and be within five minutes of server time. This current contract expects near-real-time delivery; delayed offline batch upload is not enabled.
- Measurements must be finite numbers and inside the ranges above.
- The API derives school and student assignment from the provisioned device and current bracelet assignment. The payload cannot choose a student or school.
- Duplicate idempotency keys for the same device return the already stored observation rather than creating a second row.
- Revoked devices and inactive bracelet/student assignments are rejected.
- Store only typed measurements; no unrestricted raw sensor blobs, audio, video, or student names.
- The edge response omits school and student identifiers. The principal-only history endpoint is separately school-scoped and audited.

## Privacy boundary and six-agent integration

- Individual wearable history is restricted to the school principal role and access is audited.
- The six-agent orchestrator receives only school-level wearable device-reporting coverage, and only when at least ten distinct students report within the last 24 hours.
- Heart rate, HRV, skin temperature, activity and EDA values are not sent to the six-agent pipeline.
- No diagnosis, emotion inference, disciplinary finding, automated intervention, or emergency determination is made from wearable values.
- All findings require human review. Device-originated observations are stored as `live_unverified` but have `validation_status=pending_hardware_verification`; they are excluded from school coverage and the six-agent pipeline until a supervised hardware-validation and approval workflow is implemented and completed. Authentication alone does not establish physical sensor capability, calibration, or signal quality.

## Hardware information still required

Before enabling a live pilot, obtain from the WAI hardware/firmware team:

1. Exact model, sensor part numbers and enabled sensor list.
2. HR/HRV algorithm, HRV window and quality flags.
3. Skin-temperature sensor placement and calibration method.
4. Movement/activity encoding and scale definition.
5. Whether EDA/GSR exists on the selected model, plus its unit and calibration.
6. Sampling interval, batching behaviour, clock source and offline buffering.
7. Transport/gateway protocol (BLE, Wi-Fi, LoRa or another confirmed transport), encryption and firmware update process.
8. Battery reporting semantics and device serial/firmware identifiers.

Do not infer or invent any of these values. Confirm them against the actual hardware before mapping sensor output to this API.
