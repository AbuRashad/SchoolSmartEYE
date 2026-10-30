# WAI Hardware Capability Registry

Status: scaffold only. No final WAI model or transport has been selected.

The version-controlled registry is `edge-agent/device_profiles.json`. It is
intentionally empty until an exact candidate model is selected and supported
by evidence. Do not add guessed sensors, transport details, sampling rates,
calibration claims, or firmware identifiers.

## Profile fields

- Stable profile ID
- Manufacturer and exact model name
- Hardware revision and firmware version
- Confirmed transport: BLE, Wi-Fi, LoRa, USB, Ethernet, or another documented type
- Confirmed sensor capabilities: heart rate, HRV, skin temperature,
  movement/activity, and optional EDA
- Sampling interval, if confirmed
- Calibration method, if documented
- Evidence references
- Verification status

## Verification states

1. `pending`: candidate information recorded; not approved for live ingestion.
2. `specification_reviewed`: vendor documentation reviewed; physical pilot pending.
3. `pilot_verified`: supervised hardware test evidence exists for the exact
   hardware and firmware profile.

The validator rejects `pilot_verified` without supervised hardware test
evidence. A datasheet alone does not constitute a physical pilot.

Profiles describe device capabilities only. They do not establish clinical
validity or support diagnosis, emotion inference, disciplinary decisions, or
automated interventions. Human review remains mandatory.

The profile registry is separate from student assignments and device secrets.
Never put student data, API credentials, or personal information in a profile.
