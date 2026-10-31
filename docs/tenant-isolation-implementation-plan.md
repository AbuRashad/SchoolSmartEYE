# Tenant Isolation Implementation Plan

## Decision status

Partially implemented on 2026-10-31. Migrations `0003` and `0004` introduce school membership, nullable `students.school_id`, and nullable `zones.school_id`. Server-side membership and tenant scoping are implemented for the pedagogical agent, attendance-risk, student CRUD/profile/history, zones, bracelet CRUD/ping, and camera routes. The student portal mock was removed until a real authenticated parent/student identity link exists. Existing unassigned students/zones are not auto-backfilled.

This is **not** complete tenant isolation and does not authorize production multi-school use. The migration intentionally does not backfill existing users or student records. Existing unassigned records must be mapped only through a verified ownership process. Remaining endpoints and school-owned tables still require inventory, scoping, and negative cross-tenant tests.

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
- Removed the static mock student portal response; a real parent/student account link is still required.
- Added negative regression tests for cross-school attendance aggregation, guessed student IDs, unauthorized school selection, portal mock-data removal, and student CRUD/profile/history isolation.
- Added `zones.school_id` via migration `0004`, assigned newly seeded demo zones to the demo school, and filtered `/zones` by authenticated school. Legacy zones remain unassigned until verified mapping.
- Scoped bracelet list/create/update/delete through the owning student's school; bracelet ping now verifies the target zone belongs to that same school.
- Added cross-school bracelet regression tests.
- Scoped camera list/register/start/stop/delete/snapshot/stream through persisted camera records joined to a school-owned zone; registration rejects cross-school zones and unregistered camera sources are not exposed.
- Disabled dashboard REST and WebSocket feeds because their snapshot/cache manager is process-global.
- Disabled hard-coded global analytics and report metrics until data provenance and school scope are implemented.
- Disabled simulated SSI, global unit-health/alert summaries, and process-global runtime settings until per-school source/configuration storage exists.
- Added cross-school camera registration/lifecycle denial tests. Dashboard, analytics, reports, SSI, unit-health and process-global settings remain fail-closed until their source data is partitioned by school.

Still required:
- Implement verified ownership for incidents and remaining operational stores, plus per-school runtime settings. SSI snapshot/drill ownership columns are already implemented in migration `0005`; this change adds school-filtered SSI history persistence; legacy rows still require verified mapping, and live SSI remains disabled until sensor/forecast inputs and runtime caches are school-partitioned. Re-enable dashboard/analytics/report/live-SSI/unit-health endpoints only with school-filtered queries and per-school streaming/cache partitions.
- Incident list/detail/create/resolve and drill list/detail/create/complete endpoints are implemented with server-resolved school scope. Notification management remains withheld until parent/student identity and recipient authorization are complete. Continue auditing attendance-write, analytics, SSI, report, and export endpoints.
- Add tenant ownership or a validated parent relationship to every remaining school-owned table and every in-memory/cache source; add class-level authorization and audit logging.
- Define a safe, reviewed backfill for existing users, students, and operational data. Never assign all existing rows to the demo school by default.
- Add migration upgrade/downgrade tests against the supported database engines and full API isolation matrix tests.
- Resolve parent/student authentication and membership before restoring portal profile data.
- Complete security review before any real student data or multi-school pilot.


## SSI history isolation progress — 2026-10-31

- Reuses the existing migration `0005_school_scope_ssi_and_drills.py` already present on the base branch; no duplicate Alembic revision is introduced. Its nullable `school_id` foreign keys and indexes do not infer legacy ownership.
- SSI snapshot creation, polling de-duplication, history reads, and summaries now require a school ID and apply it in every database query.
- Historical SSI API now returns only the authenticated school's snapshots. Live SSI remains fail-closed because sensor/forecast sources and runtime caches are not yet partitioned by school.
- Added regression coverage for cross-school history separation and independent polling intervals.
- Drill API/service inventory and verified ownership mapping for pre-existing SSI/drill rows remain outstanding.


## Incident and drill API isolation progress — 2026-10-31

- Added incident list/detail/create/resolve endpoints. Every incident query joins its persisted zone and filters by the authenticated school's `school_id`; create rejects zones outside that school.
- Added drill list/detail/create/complete endpoints. Every drill read and mutation filters by the authenticated school's `school_id`; new drills receive school ownership from the server, never from request data.
- Legacy incidents attached to unassigned zones and drills with null school ownership are not returned.
- Added cross-school denial tests for guessed incident/drill IDs, foreign-zone incident creation, and school assignment on drill creation.
- No notification-management API was added: the existing profile notification read is scoped through the student relationship, while standalone parent access remains blocked pending verified parent/student identity links.
- Automated test execution and production deployment remain pending.
