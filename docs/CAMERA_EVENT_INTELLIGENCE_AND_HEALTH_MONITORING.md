# Camera Event Intelligence and Health Monitoring

## Decision

The camera subsystem uses a hybrid operating model:

1. Event-triggered video analysis when a camera, edge gateway, or compatible video-management system reports motion or a configured event.
2. Continuous camera-health monitoring, independent of event detection.

This decision does not authorize continuous frame-by-frame analysis of every stream.

## Goals

- Treat cameras as the highest-priority input domain in the first implementation phase.
- Detect and triage safety-relevant events with bounded, explainable processing.
- Detect camera and stream failures even when no motion event occurs.
- Feed normalized findings into the central SchoolSmartEYE orchestration layer.
- Preserve privacy, human oversight, and a complete audit trail.

## Processing paths

### A. Event path

1. Receive an event notification from a camera, edge gateway, or VMS adapter.
2. Authenticate the source and validate the camera registration, school, timestamp, event type, and payload size.
3. Apply deduplication and rate limiting.
4. Create an immutable event envelope containing school_id, camera_id, source_id, event_id, event_type, observed_at, received_at, and source status.
5. If permitted and technically available, analyze a short event-associated clip or selected frames locally/on the edge. Do not require continuous central video upload.
6. Run camera-domain specialist analysis and produce structured findings: event category, confidence, severity, evidence references, model/rule version, and limitations.
7. Send the finding to the central orchestrator for correlation with other permitted aggregate signals.
8. Create a human-review alert. The alert is an indicator, not a confirmed incident or disciplinary conclusion.
9. Record source, timestamps, confidence, processing outcome, reviewer action, and audit events.

### B. Camera-health path

Run periodic health checks independently of event notifications. Track at minimum:
- Stream reachability and connection state
- Last successful frame / heartbeat time
- Stream latency and frame freshness
- Image availability and basic quality indicators where technically supported
- Camera or edge-agent heartbeat
- Repeated disconnects, timeouts, and recovery events
- Configuration or credential failures without logging secrets

Health checks should emit normalized status observations and operational alerts. A camera being online does not prove that its field of view is adequate; coverage validation is a separate commissioning task.

## Initial event taxonomy

Start with configurable, site-approved event categories:
- Motion in a configured monitored zone
- Entry into a restricted zone
- Unusual crowding or density threshold
- Possible fall or person-down indicator, only where validated
- Camera obstruction or scene change, if supported
- Other configured safety/security events

Do not claim that these events are reliably detectable until each detector has been evaluated in the target environment. False positives, false negatives, occlusion, lighting, camera angle, and scene-specific limitations must be measured.

## Privacy and safety controls

- Prefer on-premises or edge processing where feasible.
- Do not implement face recognition, identity matching, emotion inference, or sensitive-trait inference.
- Do not retain raw video continuously as a default. Keep only short-lived event evidence when necessary, with an explicit retention policy and access controls.
- Use metadata and derived event features for central analytics wherever possible.
- Enforce school and camera-level authorization; users must only see cameras and events within their assigned school and role.
- Separate camera technical administration from incident review permissions.
- Require human review before an alert is treated as a confirmed incident or used for consequential action.
- Preserve reviewer identity, decision, reason, and timestamp in append-only audit records.
- Define retention, access, signage, and safeguarding policies with the school and applicable law before live deployment.

## Integration contracts

Use provider-neutral adapters so the core system does not depend on a single camera vendor or VMS.

Suggested normalized records:

### CameraRegistry
- id, school_id, site_id, zone_id
- provider, external_camera_ref
- enabled, configured_event_types
- expected_heartbeat_interval
- privacy/retention policy reference
- created_at, updated_at

### CameraEvent
- id, school_id, camera_id, source_event_id
- event_type, observed_at, received_at
- source_payload_reference (not raw video by default)
- processing_status, deduplication_key

### CameraAnalysisSnapshot
- id, school_id, camera_event_id
- analyzer_name, analyzer_version
- findings (structured, bounded JSON)
- confidence, severity, limitations
- evidence_reference, created_at

### CameraHealthObservation
- id, school_id, camera_id
- observed_at, connection_status
- heartbeat_age_seconds, stream_latency_ms
- frame_freshness_seconds, quality_status
- failure_code, source_status

### CameraReviewDecision
- id, school_id, camera_event_id
- reviewer_user_id, decision, reason, decided_at

These are proposed domain contracts, not claims that these models or endpoints already exist in the repository. Keep camera events and raw-video evidence separate from school-level AggregateObservation metrics.

## Suggested API boundaries

- POST /api/v1/cameras/{camera_id}/events — authenticated camera/VMS adapter ingestion
- POST /api/v1/cameras/{camera_id}/health — authenticated health heartbeat
- GET /api/v1/cameras/health — authorized school operations view
- GET /api/v1/camera-events/review-queue — authorized safety review queue
- POST /api/v1/camera-events/{event_id}/decision — human review decision with mandatory reason

Machine-to-machine credentials must be scoped to a registered camera or gateway and a single school. Do not accept school_id from an untrusted payload as the authorization source. Resolve school scope from the authenticated integration identity and registered camera.

## Delivery sequence

1. Camera registry, school scoping, integration identity, and health heartbeat.
2. Event ingestion, validation, idempotency, and append-only audit.
3. Rule-based event triage with explicit unverified status and human review.
4. Edge/VMS adapters and short event-evidence handling.
5. Central correlation with other specialist analyzers.
6. Detector evaluation, calibration, monitoring, and controlled rollout.

## Acceptance criteria

- Health monitoring continues when no motion events are received.
- A stream outage creates a health alert without requiring a video event.
- Duplicate source events are idempotent.
- Camera/gateway credentials cannot submit events for another school's camera.
- Event findings remain unverified until a permitted human reviewer records a decision.
- Every ingestion, analysis, and review action is auditable.
- No face recognition or identity inference is present.
- Raw video is not continuously stored by default.
- Tests cover unauthorized source, cross-school access, malformed timestamps, duplicate events, stale heartbeat, stream outage, and review authorization.

## Implementation status

This document records the approved architecture decision. The camera registry, ingestion APIs, health monitor, event analyzer, and review workflow still require implementation and tests.