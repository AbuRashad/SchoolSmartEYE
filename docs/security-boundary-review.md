# Security Boundary Review — Demo Readiness

## Scope

This is a code-review snapshot of the current demo architecture, not a penetration test, compliance certification, or claim that every route has been exhaustively audited. Findings below are based on the current ORM models, authentication dependencies, student/bracelet endpoints, analytics overview, and orchestrator documentation.

## Current status

**Do not connect real student records or use this build for live multi-school operations yet.** The current code demonstrates role-based access and several bounded agent safeguards, but it does not yet establish school-level data isolation.

## Findings and priorities

### P0 — Establish school/tenant isolation before multi-school live data

- The ORM now defines `School`, `SchoolMembership`, nullable `Student.school_id`, and nullable `Zone.school_id` through migrations `0003` and `0004`. This is a partial tenant foundation, not system-wide isolation.
- Active school scope is resolved from server-side membership. A caller-supplied `school_id` is accepted only when it matches an active membership; no membership fails closed and multiple memberships require explicit selection.
- `agent.py` now scopes student lookups, in-memory engagement snapshots, feedback reads, metrics, and baselines to the resolved school. Feedback writes reject students outside that school.
- `risk.py` and `attendance_risk.py` now join attendance records to students and constrain both individual and school-wide risk results to one school.
- `portal.py` no longer returns a hard-coded student's personal data. It returns an explicit unavailable state until an authenticated parent/student identity link exists; the frontend reflects this state.
- Migration `0003` deliberately does **not** backfill existing users or students. Existing rows without a school assignment remain inaccessible through the newly scoped agent/risk routes. Assign ownership only through a verified, reviewed mapping.
- Student list/create/update/delete and student profile/behavioral-history lookups resolve the authenticated user's active school membership. Student profile attendance history joins `AttendanceRecord` to `Student` and applies the authenticated `school_id` in the same query, rather than relying on student ID alone. Student creation assigns `school_id` server-side; guessed cross-school student IDs return 404. Student profile notification reads join through the verified student; zone labels and incident-derived status/counts join through school-owned zones. Engagement summaries are keyed to the globally unique student primary key.
- Migration `0004` adds nullable `zones.school_id`; newly seeded demo zones are assigned to the demo school and `/zones` filters by the authenticated school. Existing zones remain unassigned until an explicit verified mapping. Bracelet CRUD inherits ownership through the linked student, and bracelet ping additionally requires the target zone to belong to the same school.
- Migration `0005` adds nullable `school_id` to SSI snapshots and drills. Newly seeded records are assigned to the demo school; historical rows are not auto-backfilled. SSI history reads now filter by the authenticated school, while live SSI remains disabled because its sensor/forecast inputs are still shared.
- Camera list/register/start/stop/delete/snapshot/stream routes verify a persisted `Camera` record joined to a `Zone` owned by the authenticated school. Registration rejects zones from other schools; unregistered legacy sources are not exposed. Dashboard REST summary/alerts/heatmap/live now query school-owned students, attendance, incidents, cameras, zones, and SSI snapshots directly; the shared WebSocket stream remains disabled.
- Analytics overview and ministry report list/stat now generate on-demand views from authenticated-school SQL records. Attendance is joined through Student; incidents and cameras are joined through school-owned Zones; SSI history filters by school. Report previews are explicitly marked non-persisted and do not imply downloadable artifacts. Simulated live SSI, global unit-health/alert summaries, and process-global runtime settings remain withheld. Historical SSI is enabled only for snapshots with an explicit school assignment; service-level write, polling, and history helpers reject missing school scope.
- Runtime settings are still held in a process-global singleton. The school-facing GET/PATCH API fails closed, but internal consumers remain: camera ingestion reads global FPS/JPEG/reconnect values, while bracelet and student profile serialization read the global low-battery threshold. These values currently behave as deployment-wide defaults, not per-school configuration; do not expose per-school editing until persisted school-keyed settings and consumer propagation are implemented.
- Remaining unscoped surfaces include live SSI sensor/forecast inputs, legacy unassigned SSI/drill rows, global runtime settings, the shared dashboard WebSocket/cache pipeline, exports/downloadable report artifacts, and several operational/in-memory service paths. Drill list/detail/create/complete APIs filter by the authenticated school; unassigned legacy drills remain hidden. Student-profile attendance queries join through Student and filter by school. Profile notification reads require both the student's school and matching current parent_id; no standalone parent notification API exists. Incident list/detail/create/resolve APIs enforce school ownership through the persisted zone relationship. Static unit metadata is not school data; live unit health is withheld. These still prevent any claim of complete multi-school isolation.
- Role-based authorization answers what role a user has; it does not prove which school's records that user may access.

**Required before live multi-school use:** complete tenant ownership or validated tenant relationships across every school-owned table and in-memory/demo source; apply scope filters to every read/write path; and add cross-tenant denial tests for list, detail, create, update, delete, attendance, bracelet, notification, incident, analytics, and reporting paths. Do not infer tenant identity from client-supplied IDs alone.

### P1 — Replace demo analytics with a provenance-aware data source

- `GET /analytics/overview` now returns attendance, incidents, cameras, and SSI history derived from the authenticated school's persisted records. Attendance uses a Student join; incidents/cameras use school-owned Zone joins. The response identifies its database provenance and documents that attendance rates use recorded rows only.
- The orchestrator consumes this overview. As a result, a successful response is not evidence of live school conditions.

**Required:** make demo/live mode explicit in the API and UI; label all demo metrics visibly; include source and freshness metadata for live metrics; reject or clearly flag stale/missing inputs; and test that demo values cannot be mistaken for live observations.

### P1 — Review student-sensitive endpoint exposure

- Student profiles can include attendance, last-seen zone, bracelet details, parent identifiers, notifications, and behavioral/engagement summaries.
- Student profile and behavioral-history routes now enforce school membership. Profile notifications are returned only when both the linked student belongs to the authenticated school and the notification recipient matches that student's current `parent_id`; mismatched/stale recipient rows are withheld. This does not establish an authenticated parent account link or authorize parent-facing notification access. Class-level authorization, field minimization by role, and access auditing remain outstanding.

**Required:** define per-school and, where applicable, class/student-level authorization; minimize returned fields by role and purpose; audit access to behavioral history and location-related data; and verify authorization failures with tests.

### P1 — Keep external model use opt-in and privacy-reviewed

- The optional Ollama summary path is documented as sending validated aggregate metrics to a configured provider; free-form task text is not forwarded.
- Aggregate metrics may still be sensitive when small cohorts or rare incidents are involved. “Aggregate” does not automatically mean anonymous.

**Required:** keep the deterministic provider as the default; require institutional approval before enabling external providers; document provider endpoint, retention, residency, and access controls; minimize metrics; and test that identifiers and free-form task text never reach the provider.

### P2 — Harden and verify the migration/runtime path

- Alembic migrations exist, while application configuration also supports automatic table creation.
- Tenant migration will affect existing rows and must not silently assign production data to an arbitrary school.

**Required:** plan an explicit backfill for existing records, fail safely when ownership is unknown, test upgrade/downgrade on disposable databases, and use migrations rather than automatic schema creation in production.

## Recommended implementation sequence

1. Keep the current demo isolated from real student data.
2. Complete schema ownership for notifications, incidents, SSI snapshots, drills, settings, and remaining operational stores.
3. Add explicit verified ownership backfills for legacy students, zones, cameras, and dependent records; never guess tenant ownership.
4. Apply server-side school scope to every remaining endpoint, service, background task, cache, and export.
5. Add cross-tenant denial tests for every CRUD and streaming route, including negative tests for guessed IDs.
6. Separate demo/live analytics and include provenance/freshness; re-enable currently withheld feeds only after source-level tenant scoping.
7. Re-run the complete test suite and review migrations on a disposable database.
8. Only then conduct a formal privacy/security review and consider a controlled pilot.

## Existing safeguards worth preserving

- The orchestrator requires principal-level access, rejects unknown request fields, and declares human review required.
- The orchestration response explicitly says no autonomous action was taken.
- The specialist stages are deterministic Python functions; they should not be described as six independent autonomous LLM agents.
- The optional LLM summary should never override deterministic evidence or safety boundaries.

## Validation note

This document records static code observations only. It does not claim that the full test suite passed, that a penetration test was performed, or that the application is production-ready.


## Internal service and report helper audit — 2026-10-31

- The internal `get_school_metrics` aggregation now requires an explicit school ID and scopes attendance through Student, student totals directly, and incidents/cameras through school-owned Zones. Its SSI score remains a fixed illustrative placeholder; it is not a live measurement. Dashboard APIs remain fail-closed.
- `/reports/list` and `/reports/stats` now generate school-scoped on-demand previews from persisted attendance, incident, and SSI records. They are not persisted report artifacts and no standalone export/download route exists.
- `MinistryReportService` and `ReportGenerator` are in-memory transformation helpers, not authorization boundaries. Their inputs are caller-supplied collections and the helper DTOs do not independently prove school ownership. Do not connect them to a user-facing report/export route until a server-side, school-scoped data-loading layer supplies validated inputs.
- `ParentPortalService` and the in-memory attendance-safety integration use student/child IDs but do not carry an authenticated school scope. The current `/portal/student` route does not invoke these helpers and returns an explicit `identity_link_required` state. Keep the helpers disconnected from authenticated parent access until verified parent identity, student linkage, and school-scoped data loading are implemented.
- The legacy `DashboardService` still contains synthetic seeded indicators and is no longer used by the restored REST dashboard routes. REST data is SQL-derived and school-scoped; the WebSocket stream remains disabled.


## Dashboard, analytics, and report restoration — 2026-11-01

- Dashboard REST summary, alerts, heatmap, and live snapshot now use direct SQL queries scoped to the authenticated school. SSI is shown only when an explicit school-owned snapshot exists. Heatmap intensity is an incident-derived signal, not a camera-derived or predictive risk score.
- The shared dashboard WebSocket remains disabled because its broadcaster/cache is not partitioned by school.
- Analytics overview joins attendance through Student and incidents/cameras through school-owned Zones. Missing attendance rows are not inferred as present or absent.
- Ministry report list/stat now return three on-demand previews derived from the authenticated school's records. Each preview has `persisted: false`; downloadable/stored artifacts are not implemented.
- Student and bracelet create conflicts now use neutral messages and no cross-school existence preflight. Current schema still uses globally unique student IDs, bracelet IDs, and MAC addresses; this is a schema-level limitation, not proof of per-school identifier namespaces.
- Existing profile attendance, notification, and incident-derived fields are scoped in their SQL joins/filters. Attendance-risk, dashboard, analytics, and report aggregates also use Student/Zone ownership joins. There is no standalone attendance CRUD/ingestion API or notification-management API in the current router; the pure in-memory `attendance_safety_integration` and `ParentPortalService` helpers do not enforce tenant ownership themselves and must remain disconnected from authenticated school/parent routes until supplied by a server-side school-scoped loader. Standalone parent notification access remains unavailable.
- Legacy records with null school ownership remain inaccessible to school-scoped routes. No automatic backfill or production data reassignment is authorized by this change.


## Verified parent identity — 2026-11-01

- Added `parent_student_links` as an audited mapping from a parent login (`users.id`, role exactly `parent`) to a student and school. Each active mapping requires a verifier user, verification timestamp, and verification method.
- Only a principal with an active school membership can create or revoke a mapping. The server resolves the principal's school and assigns it; clients cannot submit `user_id`, `school_id`, verifier identity, or verification timestamp.
- Parent read routes require the exact `parent` role and an active, verified mapping. Queries join the link to the student on both student_id and school_id. A parent cannot create or self-activate a link.
- Parent summaries expose only the linked student's last seven days of persisted attendance and notifications whose parent_id still matches the student's current parent reference. They do not expose camera frames, live location, raw detections, or internal risk signals.
- Parent account creation and out-of-band identity verification are not automated. The school must verify the adult against its authoritative records before a principal provisions the link. Parent login credentials must be issued through a separate secure account-provisioning process.
- Migration 0006 creates the mapping table only; it does not backfill or infer any parent links. Existing parent_id values are not treated as proof of account identity.
