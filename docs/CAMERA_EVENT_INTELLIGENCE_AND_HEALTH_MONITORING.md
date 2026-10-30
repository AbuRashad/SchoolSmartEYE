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


## CPU-first Computer Vision decision

The first deployment target is CPU-only. The camera pipeline must not require an NVIDIA GPU, a hosted inference API, or a paid AI service.

### Processing design

- Use OpenCV or an equivalent decoder/vision utility for RTSP/VMS stream handling, frame sampling, region-of-interest operations, and image-quality checks.
- Use a compact object-detection model for person/object detection. Select the exact model only after checking its license, model provenance, supported runtime, and measured accuracy on representative school footage.
- Use multi-object tracking (for example, a ByteTrack-style tracker) to associate detections across sampled frames. Tracking identifiers are temporary scene-local IDs, not identities.
- Add pose estimation or action recognition only for narrowly defined use cases, such as a possible fall indicator, after separate validation. Do not infer intent, emotion, or identity.
- Use ONNX Runtime CPU as a portable inference option. Evaluate OpenVINO as an optional optimization on supported Intel hardware; do not make it a hard dependency.
- Run inference on sampled frames and short event windows. Do not decode and infer on every frame from every camera by default.
- Keep camera-health checks on a separate lightweight path so health monitoring continues even when the CV worker is busy or unavailable.

### CPU workload controls

- Make per-camera sampling rate, input resolution, active zones, model choice, and maximum concurrent inference jobs configurable.
- Use bounded queues, backpressure, timeouts, and per-camera fairness so one busy camera cannot starve all others.
- Prioritize safety events over routine scene summaries.
- Drop or coalesce stale intermediate frames rather than allowing an unbounded backlog.
- Expose queue depth, processing latency, dropped-frame count, CPU utilization, memory use, and per-camera processing lag.
- If capacity is exceeded, degrade gracefully: reduce sampling frequency or defer noncritical analysis, while preserving health monitoring and recording the degraded state.
- Never silently imply real-time coverage when the pipeline is behind.

### Benchmark gate before multi-camera rollout

Benchmark on the actual target CPU and representative camera streams. Record at least:
- CPU model, core/thread count, RAM, OS, runtime, and model version
- Number of concurrent streams and stream resolution/frame rate
- Sampling rate and measured inference throughput
- End-to-end event latency and queue lag
- CPU/RAM utilization and dropped-frame rate
- Precision/recall or task-appropriate detection metrics on a labeled validation set
- False-alert rate by event category and relevant scene conditions

Do not promise a camera count or real-time frame rate before this benchmark. Start with one test stream, then increase concurrency under load testing.

### CPU-first acceptance criteria

- The complete basic detection/tracking path runs without a GPU.
- Health monitoring remains responsive while inference is loaded or stopped.
- Queues remain bounded and overload is visible to operators.
- The system reports actual processing lag and does not label delayed analysis as live.
- Model/runtime licenses and provenance are recorded before deployment.
- Event categories remain unverified until validated on representative school footage.
- A failed or overloaded CV worker cannot disable camera-health monitoring.


## Development without live camera access

Live school-camera access is not currently available. This does not block architecture completion or implementation of provider-neutral components.

Until authorized camera access is provided:
- Implement and unit-test camera registry, event contracts, validation, authorization, idempotency, health-state transitions, audit records, and bounded processing queues independently of a physical camera.
- Use synthetic events and locally stored/sample video only where licensing and safeguarding permit. Clearly label these as development fixtures, not school deployment evidence.
- Keep RTSP/VMS integration behind adapters so camera vendors and connection details can be added later without changing the central intelligence contracts.
- Provide deterministic test fixtures for normal scenes, occlusion, low light, crowded scenes, camera obstruction, disconnects, stale frames, duplicate events, malformed timestamps, and overload.
- Do not use synthetic fixtures to claim field accuracy, real-world false-positive rates, supported camera counts, or production readiness.

## Deferred field-validation phase

When authorized access to representative school cameras becomes available, run a documented validation campaign before live operational use:
1. Confirm camera ownership/authorization, field of view, privacy notices, approved zones, retention, and access controls.
2. Validate RTSP/VMS compatibility and stream stability for each camera model/configuration.
3. Capture a representative, lawfully approved validation set across lighting, distance, occlusion, camera angles, and scene density.
4. Label ground truth with an approved safeguarding process; keep identities out of the dataset and evaluation outputs.
5. Evaluate each event category separately using precision, recall, false alerts per camera-hour, missed-event analysis, and confidence calibration where applicable.
6. Benchmark CPU-only and optional Intel Iris Xe execution, measuring end-to-end latency, queue lag, CPU/RAM use, dropped frames, and concurrent streams.
7. Run shadow mode first: generate review-only findings without triggering consequential actions.
8. Obtain human-review sign-off and document known limitations before enabling operational alerts.

A field-validation report must identify the exact model/runtime versions, camera configurations, dataset scope, metrics, thresholds, failures, and approval decision. Passing software tests is not equivalent to passing field validation.

## Camera Event Intelligence Engine — first implementation slice

Implemented in `app/services/camera_event_intelligence.py`:
- A detector adapter contract (`ObjectDetector`) so a local, reviewed inference runtime can be plugged in without cloud fallback.
- Structured detections with confidence and bounding-box validation.
- CPU-friendly frame downscaling with configurable maximum dimensions.
- Event candidate rules for person presence, configurable person-count screening, and optional configured restricted-zone polygon overlap.
- Immutable-style analysis snapshots with camera/zone identifiers, timestamps, model version, evidence notes, and explicit limitations.
- Every finding is marked `candidate` and `requires_human_review=true`; no identity recognition or autonomous action is included.

Tests are in `tests/test_camera_event_intelligence.py` and use a fake detector. They validate orchestration and rule behavior only; they do not measure or claim real-world detector accuracy.

**Important implementation boundary:** this slice does not yet include a production object-detection model, tracker, temporal action recognition, event-trigger adapter from the camera worker, persistent event storage, or central-orchestrator handoff. The detector must be supplied by a separately reviewed local model adapter before actual visual object detection occurs.

## Initial CPU-first software foundation

The first implementation slice now includes:
- `app/services/camera_cv_runtime.py`: validated per-camera workload configuration, monotonic frame sampling gate, and bounded latest-frame queue that drops stale pending frames under overload.
- `tests/test_camera_cv_runtime.py`: unit coverage for configuration validation, sampling cadence/reset, bounded queue behavior, and overload freshness.

These primitives are scheduling/backpressure infrastructure only. They do not decode RTSP streams, run object detection, track people, classify actions, monitor persistent camera health, or establish field accuracy. No model weights or third-party inference runtime have been added yet.

The existing live-stream endpoint/service remains a separate legacy path and has not yet been migrated to these primitives. Before enabling school deployment, its source handling, tenant isolation, credential storage, privacy behavior, and authorization need a dedicated security review.

## Implementation status

This document records the approved architecture decision. The camera registry, ingestion APIs, health monitor, event analyzer, and review workflow still require implementation and tests.

## Optional local ONNX detector adapter — initial integration boundary

Added `app/services/camera_onnx_detector.py` as an optional CPU-only adapter:
- Loads only an explicitly configured local ONNX file; it never downloads weights.
- Requests `CPUExecutionProvider` and imports ONNX Runtime lazily, so the base application does not require the optional package.
- Requires one NCHW, three-channel input and one post-NMS output tensor with rows `[x1, y1, x2, y2, confidence, class_id]` in input-image pixel coordinates.
- Resizes directly to the configured model input dimensions and maps output boxes back to the supplied frame dimensions.
- Rejects incompatible tensor shapes and non-finite output; filters unknown classes and low-confidence detections.
- Model labels, input dimensions, and confidence threshold must be explicitly configured.

Install the optional runtime only when a reviewed compatible model is selected: `pip install onnxruntime`.

**Compatibility warning:** this is not a universal YOLO adapter. Raw YOLO head outputs, transposed `[1, 4+C, N]` tensors, normalized-coordinate outputs, letterboxed exports, and models with embedded NMS but a different output contract are intentionally rejected/not supported. Do not point it at an arbitrary ONNX file. The placeholder model used in tests is not a valid inference model; tests use a fake ONNX session to verify preprocessing and the declared output contract. No real ONNX inference, model accuracy, or camera performance has been validated.
