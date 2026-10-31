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
- Camera list/register/start/stop/delete/snapshot/stream routes now verify a persisted `Camera` record joined to a `Zone` owned by the authenticated school. Registration rejects zones from other schools; unregistered legacy sources are not exposed. Dashboard REST feeds and WebSocket snapshots remain disabled until their process-global live/cache sources are partitioned by school.
- Global placeholder analytics, ministry report list/stat, simulated live SSI, global unit-health/alert summaries, and process-global runtime settings now fail closed rather than presenting hard-coded/shared state as school-specific evidence. Historical SSI is enabled only for snapshots with an explicit school assignment; service-level write, polling, and history helpers now reject missing school scope. This is a temporary availability trade-off, not completion of analytics/reporting isolation.
- Runtime settings are still held in a process-global singleton. The school-facing GET/PATCH API fails closed, but internal consumers remain: camera ingestion reads global FPS/JPEG/reconnect values, while bracelet and student profile serialization read the global low-battery threshold. These values currently behave as deployment-wide defaults, not per-school configuration; do not expose per-school editing until persisted school-keyed settings and consumer propagation are implemented.
- Remaining unscoped surfaces include live SSI sensor/forecast inputs, legacy unassigned SSI/drill rows, global runtime settings, dashboard caches, exports, and several operational/in-memory service paths. Drill list/detail/create/complete APIs filter by the authenticated school; unassigned legacy drills remain hidden. Notification reads exposed by student profiles are scoped through the verified student relationship; no standalone notification-management API is exposed until parent/student identity and recipient authorization are complete. Incident list/detail/create/resolve APIs enforce school ownership through the persisted zone relationship. Static unit metadata is not school data; live unit health is withheld. These still prevent any claim of complete multi-school isolation.
- Role-based authorization answers what role a user has; it does not prove which school's records that user may access.

**Required before live multi-school use:** complete tenant ownership or validated tenant relationships across every school-owned table and in-memory/demo source; apply scope filters to every read/write path; and add cross-tenant denial tests for list, detail, create, update, delete, attendance, bracelet, notification, incident, analytics, and reporting paths. Do not infer tenant identity from client-supplied IDs alone.

### P1 — Replace demo analytics with a provenance-aware data source

- `GET /analytics/overview` currently returns hard-coded illustrative metrics, including attendance, incidents, camera activity, and compliance.
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
- `/reports/list` and `/reports/stats` remain unavailable (503) until their source records are school-scoped. The current API endpoint inventory contains no standalone export route.
- `MinistryReportService` and `ReportGenerator` are in-memory transformation helpers, not authorization boundaries. Their inputs are caller-supplied collections and the helper DTOs do not independently prove school ownership. Do not connect them to a user-facing report/export route until a server-side, school-scoped data-loading layer supplies validated inputs.
- `ParentPortalService` and the in-memory attendance-safety integration use student/child IDs but do not carry an authenticated school scope. The current `/portal/student` route does not invoke these helpers and returns an explicit `identity_link_required` state. Keep the helpers disconnected from authenticated parent access until verified parent identity, student linkage, and school-scoped data loading are implemented.
- The dashboard service still contains synthetic seeded indicators. Dashboard routes are intentionally unavailable; these values must not be presented as live school conditions.
