# WAI Signal Quality Engine

The local edge quality engine is implemented in edge-agent/signal_quality.py.
It assesses a single wai.v1 observation against an explicitly selected hardware
capability profile. It is metadata-only and does not transmit, persist, diagnose,
or interpret a student's health or emotions.

## Checks

- Schema and documented numeric range validation through the existing gateway validator
- Sensor fields compared with the selected profile's declared capabilities
- Stale and future-dated observations using the received timestamp
- Duplicate idempotency keys when the caller supplies its seen-key set
- Missing sample windows when a verified sampling interval and previous timestamp exist
- Explicit demo versus live_unverified mode

A missing sampling interval is not guessed. Gap detection is skipped until the
selected device profile documents one. No medical thresholds or clinical meaning
are inferred from any reading.

## Data modes and coverage

Callers must explicitly select demo or live_unverified. Demo records always carry
the demo_data flag and are never eligible for live school coverage. A live_unverified
record is only marked eligible when it passes the implemented technical checks;
this is not proof that hardware is genuine, calibrated, clinically valid, or
supervised. The server remains responsible for device authentication, assignment,
tenant isolation, cohort suppression, auditing, and human review.

The function returns only quality metadata and flags, not sensor values or
student identifiers. It does not write logs or make network requests.

## Current limitations

- No WAI hardware model or transport has been selected.
- No device-specific calibration or sampling cadence has been verified.
- Duplicate detection depends on the caller supplying previously seen keys.
- The engine is not yet wired into the server ingestion or school overview path.
- Do not use synthetic records against the live ingestion endpoint.
- No diagnosis, emotion inference, disciplinary decision, or automatic intervention
  is supported. Human review remains mandatory.
