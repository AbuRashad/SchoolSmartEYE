# Tenant Isolation Implementation Plan

## Decision status

Partially implemented on 2026-10-31. Migrations `0003`–`0005` introduce school membership and nullable ownership fields for students, zones, SSI snapshots, and drills. Server-side membership and tenant scoping are implemented for the pedagogical agent, attendance-risk, student CRUD/profile/history, zones, bracelet CRUD/ping, camera routes, and SSI history. The student portal mock was removed until a real authenticated parent/student identity link exists. Existing unassigned students/zones are not auto-backfilled.

This is **not** complete tenant isolation and does not authorize production multi-school use. The migrations intentionally do not backfill existing users, student records, zones, SSI snapshots, or drills. Existing unassigned records must be mapped only through a verified ownership process. Remaining endpoints and school-owned tables still require inventory, scoping, and negative cross-tenant tests.

## Objective

Ensure each school user can access only records explicitly assigned to that school, while retaining a separately authorized Ministry-wide scope if the product requirements call for it. A role (teacher/principal/ministry) is not a substitute for a school scope.

## Proposed domain model

### School

Introduce a `schools` table with a stable primary key, unique school code, display name, status, and created/updated timestamps. Avoid using a display name as an identifier.

### User-school membership

Prefer a membership table (for example, `school_memberships`) instead of a single `school_id` on User if users may legitimately work across schools. Each membership should include user ID, school ID, role/scope, status, and optional audit fields. Enforce uniqueness for the intended user-school membership key. A Ministry-wide role should have an explicit, audited scope; do not make it an implicit bypass for all endpoints.

### School-owned data

At minimum, tenant scope must cover students and all records that are owned by or derived from a school's data. This includes attendance, bracelets, notifications, zones, cameras, incidents, safety-index snapshots, drills, feedback records, and any in-memory/demo stores or cached service data. Some child records may inherit school ownership through a validated parent relationship, but every query must prove that relationship within the same school. Do not add redundant school IDs without a consistency rule.

## Authorization contract

1. Resolve the authenticated user from the validated token.
2. Resolve an authorized school membership from server-side identity and an explicit route/query selection where multi-school users are supported.
3. Reject missing/ambiguous school scope rather than guessing.
4. Apply the same scope to reads, updates, deletes, nested records, analytics, exports, and AI context.
5. Do not trust a client-provided `school_id` as proof of access.
6. For a guessed record ID from another school, return a consistent non-disclosing response (normally 404) and do not leak the record's existence.
7. Record security-relevant access and denied cross-tenant attempts without logging sensitive student content.

## Migration and backfill safety

- Add the schools and membership structures first.
- Decide how existing demo records are assigned. Use a clearly named demo school only if the records are confirmed to be synthetic demo data.
- If any existing records may be real or their ownership is uncertain, stop and require an explicit mapping. Never silently assign unknown records to a default school.
- Add ownership constraints and indexes only after backfill has been validated.
- Use Alembic migrations; test on a disposable copy of the database before touching any persistent environment.
- Test both forward migration and rollback strategy. A rollback must not discard newly assigned ownership or silently merge schools.
- Avoid deploying an intermediate state where endpoints accept unscoped access.

## Test plan (minimum)

### Authentication and membership
- Unauthenticated requests remain rejected.
- A user with no active school membership cannot access school-owned endpoints.
- Teacher and principal role hierarchy is preserved within the authorized school.
- Ministry access is explicit and tested separately.
- A multi-school user must select only a school for which they have an active membership.

### Isolation matrix
For each endpoint family (students, profiles, behavioral history, attendance, notifications, bracelets, zones, cameras, incidents, analytics, drills, safety snapshots, agent feedback, orchestration/evidence):
- User from School A cannot list School B records.
- User from School A cannot read or modify a School B record by guessing its ID.
- Creating a child record under a School B parent is rejected.
- Related data cannot be joined across schools.
- Aggregates contain only authorized-school data.
- Cached/in-memory services cannot return cross-school results.
- Unknown or missing scope fails closed.

### Data and migration
- Empty database migration works.
- Synthetic demo data backfills to the intended demo school.
- Unknown ownership causes a safe failure, not a guessed assignment.
- Unique constraints and foreign keys remain valid.
- Tests run against the supported database engine(s), not only a mocked session.

## Implementation sequence

1. Inventory all SQL models, API routes, background jobs, seed stores, caches, and frontend calls that touch school-owned data.
2. Confirm product rules for Ministry-wide visibility and users assigned to multiple schools.
3. Implement School and membership models plus migration/backfill in a separate reviewed change.
4. Implement a reusable server-side scope resolver and enforce it in every endpoint and service query.
5. Add negative cross-tenant tests before enabling any multi-school data.
6. Mark demo analytics explicitly and scope all aggregates.
7. Run the full test suite and migration tests; review logs and response payloads for accidental data leakage.
8. Conduct privacy/security review before a controlled pilot.

## Out of scope for this design

- No code changes or database migration are performed by this document.
- No claim is made that the current system is production-ready or that the plan alone guarantees compliance.
- No real student data should be imported until tenant enforcement and authorization tests are complete.


## Implementation progress — 2026-10-31

Completed:
- Added `School` and `SchoolMembership` ORM models and Alembic revision `0003`.
- Added `Student.school_id` as nullable during controlled backfill; no default-school assignment is performed for existing records.
- Added a server-side resolver that validates any requested school against the authenticated user's active memberships, fails closed without membership, and rejects ambiguous multi-school scope.
- Scoped pedagogical agent student lookup, snapshots, feedback reads/writes, metrics, and baselines to the resolved school.
- Scoped individual and school-wide attendance risk queries through the Student join.
- Scoped student-profile attendance history through an explicit `AttendanceRecord` → `Student` join filtered by the authenticated `school_id`.
- Removed the static mock student portal response; a real parent/student account link is still required.
- Added negative regression tests for cross-school attendance aggregation, guessed student IDs, unauthorized school selection, portal mock-data removal, and student CRUD/profile/history isolation.
- Added `zones.school_id` via migration `0004`, assigned newly seeded demo zones to the demo school, and filtered `/zones` by authenticated school. Legacy zones remain unassigned until verified mapping.
- Added `school_id` to SSI snapshots and drills via migration `0005`; new demo rows are assigned to the demo school and SSI history queries are filtered by school. Legacy rows are not auto-backfilled; live SSI remains disabled.
- Scoped bracelet list/create/update/delete through the owning student's school; bracelet ping now verifies the target zone belongs to that same school.
- Added cross-school bracelet regression tests.
- Scoped camera list/register/start/stop/delete/snapshot/stream through persisted camera records joined to a school-owned zone; registration rejects cross-school zones and unregistered camera sources are not exposed.
- Dashboard REST summary/alerts/heatmap/live have been restored using school-filtered SQL queries; the shared WebSocket remains disabled because its broadcaster/cache is process-global.
- Replaced global analytics/report metrics with authenticated-school SQL aggregates and on-demand report previews. Report previews are not persisted artifacts.
- Disabled simulated SSI, global unit-health/alert summaries, and process-global runtime settings until per-school source/configuration storage exists.
- Audited runtime-settings consumers: camera ingestion uses the process singleton for stream FPS/JPEG/reconnect behavior; bracelet and student profile summaries use its battery threshold. The settings API remains fail-closed for both reads and writes. Per-school settings require persisted school-keyed configuration and explicit propagation into each consumer before re-enabling the API.
- Added cross-school camera registration/lifecycle denial tests. Dashboard REST, analytics overview, and report previews have since been restored with school-filtered SQL; dashboard WebSocket, live SSI, unit-health, and process-global settings remain fail-closed.

Still required:
- Implement verified ownership for remaining operational stores and per-school runtime settings; partition the dashboard streaming/cache layer before enabling WebSocket, and partition sensor/health inputs before enabling live SSI or unit-health feeds.
- Incident list/detail/create/resolve and drill list/detail/create/complete endpoints are implemented with server-resolved school scope. Student profile attendance, notification, and incident-derived reads are school-filtered. Analytics overview and ministry report previews are now school-scoped; previews are generated on request and are not stored. Standalone parent notification access remains withheld until verified parent/student identity mapping is complete. Continue auditing attendance-write and export/download paths.
- Add tenant ownership or a validated parent relationship to every remaining school-owned table and every in-memory/cache source; add class-level authorization and audit logging.
- Define a safe, reviewed backfill for existing users, students, and operational data. Never assign all existing rows to the demo school by default.
- Add migration upgrade/downgrade tests against the supported database engines and full API isolation matrix tests.
- Resolve parent/student authentication and membership before restoring portal profile data.
- Complete security review before any real student data or multi-school pilot.


## SSI service-level scope guards — 2026-10-31

- SSI snapshot creation, polling de-duplication, and history reads now reject empty or missing school IDs before issuing database operations.
- Regression tests verify that unassigned legacy snapshots remain invisible, polling windows do not cross schools, and service helpers fail closed without tenant scope.
- Existing migration 0005 and school-filtered API behavior are reused; this change adds no schema migration.


## Incident and drill API isolation progress — 2026-10-31

- Added incident list/detail/create/resolve endpoints. Every incident query joins its persisted zone and filters by the authenticated school's `school_id`; creation rejects zones outside that school.
- Added drill list/detail/create/complete endpoints. Every drill read and mutation filters by the authenticated school's `school_id`; new drills receive school ownership from the server, never from request data.
- Legacy incidents attached to unassigned zones and drills with null school ownership are not returned.
- Added cross-school denial tests for guessed incident/drill IDs, foreign-zone incident creation, and server-side tenant assignment.
- No notification-management API was added: existing profile notification reads are scoped through the student relationship, while standalone parent access remains blocked pending verified parent/student identity links.
- Automated test execution and production deployment remain pending.


## Student profile attendance query hardening — 2026-10-31

- The profile attendance-history query now joins the owning `Student` row and filters by the authenticated school's `school_id` in the same SQL statement.
- This is defense in depth alongside the profile's initial school-scoped student lookup; it avoids relying solely on globally unique student IDs as the tenant boundary.
- No schema change or data migration was needed.


## Internal metric/report/portal helper audit — 2026-10-31

- `get_school_metrics` now requires an explicit school ID and filters attendance, student totals, incidents, and cameras to that school. Regression tests create a second school and verify that its records do not change the first school's metrics. The SSI value in this helper remains illustrative, not live.
- Ministry report and semester report generators are pure transformations over caller-supplied collections; they must receive data from a separately authorized school-scoped loader before any API/export integration.
- Parent portal and attendance-safety in-memory helpers do not independently enforce school ownership. The authenticated portal endpoint remains unavailable until verified parent/student identity mapping and school-scoped loading are complete.
- There is no standalone export endpoint in the current API router inventory; report list/stat routes remain fail-closed.


## Demo endpoint restoration and conflict-message hardening — 2026-11-01

- Student creation no longer performs a global preflight lookup for a submitted student ID. Database uniqueness conflicts return a neutral message without echoing the identifier.
- Bracelet creation no longer performs a global MAC-address preflight lookup. Bracelet ID/MAC database conflicts return the same neutral response and do not disclose the conflicting value or owning school.
- Dashboard REST summary, alerts, heatmap, and live snapshot now use authenticated-school SQL queries. The heatmap is explicitly an incident signal, not camera-derived prediction. WebSocket remains disabled.
- Analytics overview and Ministry report previews now query only authenticated-school data. Report previews are on-demand and explicitly non-persisted.
- Regression tests cover cross-school student/bracelet conflict responses, dashboard isolation, analytics isolation, and report preview isolation.
- **Legacy data decision:** no automatic backfill is permitted. Before any real deployment/import, an authorized data owner must approve a record-by-record or source-of-truth-based school ownership mapping, define treatment of ambiguous/unassigned records (retain inaccessible or quarantine), approve a backup/rollback plan, and sign off on migration dry-run results. No migration or reassignment is performed in this PR.
- **Identifier decision still required:** `Student.student_id`, `Bracelet.bracelet_id`, and `Bracelet.mac_address` are globally unique in the current schema. Neutral error messages reduce disclosure but do not create school-local identifier namespaces. If schools may reuse student/bracelet identifiers, introduce surrogate primary keys plus school-scoped unique constraints in a separately reviewed schema migration.


## Data provenance and remaining API boundaries — 2026-11-01

- Dashboard, analytics, reports, and orchestration explicitly label the demo tenant's seeded records as synthetic demo data, not live telemetry. Other tenants are marked unknown until record-level provenance is verified.
- Attendance reads in student profiles, attendance-risk, dashboard, analytics, and report previews are scoped through the owning Student row. There is no standalone attendance CRUD/ingestion endpoint in the current API router.
- Notification reads are limited to the student profile and require a school-owned Student join plus matching current parent_id. No standalone notification-management or parent-facing API is exposed.
- Incident list/detail/create/resolve and dashboard/analytics/report incident aggregates inherit school ownership through the persisted Zone join. Unassigned legacy zones and their incidents remain inaccessible.
- The in-memory attendance-safety and parent-portal helpers do not independently enforce tenant scope; keep them disconnected from authenticated routes until a verified, school-scoped data loader is introduced.


## Parent identity implementation — 2026-11-01

- Added migration 0006 and the `ParentStudentLink` model. Links are unique by parent user, student, and school, and carry verifier, verification timestamp, method, and active/revoked state.
- Added principal-only create/revoke endpoints. The school is derived from the principal's active membership; the student must belong to that school; the selected account must already exist, be active, and have role exactly `parent`.
- Added parent-only read endpoints for linked students and minimal student summaries. Parent access requires a verified active link joined to the student using both student_id and school_id.
- Parent summaries include only persisted attendance for the linked student and notifications still addressed to the student's current parent reference. Live location, camera detections, and internal safety signals remain withheld.
- No parent accounts are auto-created, no parent-child links are auto-inferred, and no existing parent_id is treated as authentication proof. School identity verification and secure parent account provisioning remain operational prerequisites.
- The new migration is additive and has not been run against production. No legacy data was backfilled.
