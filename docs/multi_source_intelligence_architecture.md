# SchoolSmartEYE Multi-Source Intelligence Architecture

## Purpose

SchoolSmartEYE is a governed school-intelligence platform, not a camera-only product. It combines evidence from independently managed sources and routes validated, privacy-minimised information through six specialist agents and one coordinating orchestrator.

This document records the integration contract before adding new persistence or device protocols. It deliberately does not assume which physical sensors the WAI (وعي) wristband contains.

## Existing six-agent pipeline

The current implementation is in `app/services/agent_orchestrator.py` and `app/services/specialist_agents.py`:

1. Analytics
2. Safety
3. Academic
4. Operations
5. Evidence
6. Ethics review

The orchestrator is the coordinator. Specialist outputs are advisory, evidence is allowlisted aggregate numeric data, and every report requires human review. No autonomous action is permitted. Native model output, when enabled, must not override deterministic findings or evidence.

## Source domains

### Camera intelligence
- Camera connectivity and health telemetry.
- Camera-derived events enter a human review queue.
- Camera health is operational telemetry, not proof of student behaviour or identity.
- Real camera connectivity has not yet been field-tested in this development environment.

### WAI wearable intelligence
- The bracelet registry already exists in `app/db/models.py` and the API in `app/api/v1/endpoints/bracelets.py`.
- The founder's WAI/SchoolSmartEYE concept documents describe these proposed signal families: heart rate (bpm), heart-rate variability (HRV, milliseconds), skin temperature (°C), movement/activity, and optional electrodermal activity (EDA/GSR, device-dependent).
- These are the intended integration fields, not proof that a particular wristband model or firmware currently exposes them. EDA/GSR is explicitly optional. Hardware model, exact HRV method, movement encoding, sampling rates, calibration, transport, and firmware payload still require confirmation before live ingestion.
- The current bracelet ping endpoint updates battery level and last-seen zone; it is not yet a general wearable sensor-ingestion protocol.
- Do not assume heart-rate, temperature, GPS, fall-detection, sleep, or other sensor availability until the actual WAI hardware specification is confirmed.
- Future wearable observations must be timestamped, device-authenticated, replay-resistant, school-scoped, and linked to an authorised bracelet/student assignment.
- Store only the minimum required normalized measurements. Do not retain unrestricted raw payloads by default.
- Distinguish device-health telemetry (battery, firmware, last-seen) from student-related observations.
- Any wellbeing-related signal is a prompt for an authorised human to check context, never a diagnosis, behavioural label, disciplinary finding, or automated emergency determination.

### School information systems
- Attendance, academic aggregates, and operational records.
- Student-level records must not be passed into the six-agent aggregate pipeline.
- Source freshness, provenance, validation state, and tenant ownership must accompany imported data.

## Required ingestion contract

Every source adapter should produce a normalized observation envelope with:

- `source_type`: camera, wearable, or school_system.
- `source_id`: registered device or integration identifier.
- `school_id`: tenant boundary derived from authenticated device/user registration, never trusted from an unverified payload.
- `observed_at`: timezone-aware source timestamp.
- `received_at`: server receipt timestamp.
- `schema_version`: explicit payload version.
- `idempotency_key`: bounded replay/deduplication key.
- `validation_status`: pending, accepted, or rejected.
- `data_status`: demo, live_unverified, or live_verified.
- A minimal typed observation body; no arbitrary free-form student profile or raw video/audio.

Adapters must reject non-finite numeric values, invalid timestamps, unknown schema versions, oversized payloads, inactive devices, cross-school references, and duplicate/replayed events.

## Cross-source intelligence flow

1. Authenticate the source and establish its school scope.
2. Validate schema, timestamp, device assignment, and idempotency.
3. Persist a minimal normalized observation with provenance and audit history.
4. Apply deterministic source-specific validation and aggregation.
5. Pass only approved school-level aggregates and evidence references to the six specialist agents.
6. The Evidence agent records source/freshness limitations; the Ethics Review agent checks the combined output.
7. Present findings for human review. No automatic student-level action.

Cross-source correlation may identify a reason to verify information, but it must not turn temporal coincidence into causation. Conflicting sources must remain visible as conflicts rather than being silently merged.

## Privacy and governance requirements

- Tenant isolation is mandatory for every source, observation, query, and report.
- Use pseudonymous internal identifiers in processing paths where practical.
- Do not expose student names, contact details, MAC addresses, or raw wearable readings to external LLM providers.
- Native intelligence runs inside SchoolSmartEYE by default. No external AI provider is contacted by default.
- Any external AI connection requires an explicit, documented request from an authorised principal/school leader; it remains advisory and cannot override deterministic rules.
- Retention periods, guardian notices/consent, school policy, and applicable law must be settled before any live student wearable deployment.
- Access to individual-level records is role-restricted and audited.
- A human reviewer must be able to see provenance, timestamp, validation status, and limitations before acting.

## Current implementation gaps to close

1. Bracelet management and simulated location/battery ping exist, but authenticated wearable-device credentials and a general observation history do not.
2. The current `Student` model has no explicit `school_id`; this must be addressed before multi-school wearable ingestion can be safely enabled.
3. The camera registry still has an in-memory/configuration component; persistent source registration remains a separate integration task.
4. The actual WAI hardware sensor list, transport protocol, sampling rates, units, and firmware payload are not yet confirmed.
5. Cross-source aggregate derivation and provenance-aware orchestrator input are not yet wired end-to-end.

## Implementation sequence

1. Confirm WAI hardware fields and transport protocol; keep unknown sensors disabled.
2. Add explicit student/bracelet tenant ownership and migration/backfill.
3. Add per-bracelet device identity, one-time secret provisioning, rotation/revocation, and authenticated ingestion.
4. Add typed, minimal, idempotent wearable observation persistence and audit events.
5. Add deterministic aggregation that emits only allowlisted school-level metrics to the six-agent orchestrator.
6. Add dashboard views for device health, source freshness, and human-review-required signals.
7. Test with synthetic payloads first; only then conduct a supervised hardware pilot.

## Non-goals

- No facial recognition or identity inference from camera footage.
- No medical diagnosis from wearable measurements.
- No automated punishment, grading, student profiling, or parent notification based solely on an AI-generated inference.
- No claim of live camera or wearable operation until a real device integration has been tested.
