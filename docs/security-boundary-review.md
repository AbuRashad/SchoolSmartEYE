# Security Boundary Review — Demo Readiness

## Scope

This is a code-review snapshot of the current demo architecture, not a penetration test, compliance certification, or claim that every route has been exhaustively audited. Findings below are based on the current ORM models, authentication dependencies, student/bracelet endpoints, analytics overview, and orchestrator documentation.

## Current status

**Do not connect real student records or use this build for live multi-school operations yet.** The current code demonstrates role-based access and several bounded agent safeguards, but it does not yet establish school-level data isolation.

## Findings and priorities

### P0 — Establish school/tenant isolation before multi-school live data

- The ORM now defines `School`, `SchoolMembership`, and nullable `Student.school_id` fields through migration `0003`. This is a partial tenant foundation, not system-wide isolation.
- Active school scope is resolved from server-side membership. A caller-supplied `school_id` is accepted only when it matches an active membership; no membership fails closed and multiple memberships require explicit selection.
- `agent.py` now scopes student lookups, in-memory engagement snapshots, feedback reads, metrics, and baselines to the resolved school. Feedback writes reject students outside that school.
- `risk.py` and `attendance_risk.py` now join attendance records to students and constrain both individual and school-wide risk results to one school.
- `portal.py` no longer returns a hard-coded student's personal data. It returns an explicit unavailable state until an authenticated parent/student identity link exists; the frontend reflects this state.
- Migration `0003` deliberately does **not** backfill existing users or students. Existing rows without a school assignment remain inaccessible through the newly scoped agent/risk routes. Assign ownership only through a verified, reviewed mapping.
- Student list/create/update/delete and student profile/behavioral-history lookups now resolve the authenticated user's active school membership. Student creation assigns `school_id` server-side; guessed cross-school student IDs return 404. Student profile withholds notifications, incident-derived status/counts, and zone labels because those source records are not yet tenant-scoped. The engagement summary is keyed to the globally unique student primary key.
- The `/zones` endpoint currently fails closed with 503 because `zones` has no school ownership field. Bracelet/attendance student-linked detail remains scoped through the verified student record, but bracelet, camera, incident, zone, notification, and other operational routes still require a full audit and schema-level tenant ownership.
- Camera REST/snapshot/stream operations now fail closed because the ingestion registry is process-global and has no verified school owner. Dashboard REST feeds and WebSocket snapshots are also disabled until their process-global live/cache sources are partitioned by school.
- Global placeholder analytics, ministry report list/stat, simulated SSI, global unit-health/alert summaries, and process-global runtime settings now fail closed rather than presenting hard-coded/shared state as school-specific evidence. This is a temporary availability trade-off, not completion of analytics/reporting isolation.
- Remaining unscoped surfaces include notification records, incidents, SSI snapshots, drills, camera/zone persistence and ingestion configuration, and other operational, export, and in-memory service paths. Static unit metadata is not school data; live unit health is withheld. These still prevent any claim of complete multi-school isolation.
- Role-based authorization answers what role a user has; it does not prove which school's records that user may access.

**Required before live multi-school use:** complete tenant ownership or validated tenant relationships across every school-owned table and in-memory/demo source; apply scope filters to every read/write path; and add cross-tenant denial tests for list, detail, create, update, delete, attendance, bracelet, notification, incident, analytics, and reporting paths. Do not infer tenant identity from client-supplied IDs alone.

### P1 — Replace demo analytics with a provenance-aware data source

- `GET /analytics/overview` currently returns hard-coded illustrative metrics, including attendance, incidents, camera activity, and compliance.
- The orchestrator consumes this overview. As a result, a successful response is not evidence of live school conditions.

**Required:** make demo/live mode explicit in the API and UI; label all demo metrics visibly; include source and freshness metadata for live metrics; reject or clearly flag stale/missing inputs; and test that demo values cannot be mistaken for live observations.

### P1 — Review student-sensitive endpoint exposure

- Student profiles can include attendance, last-seen zone, bracelet details, parent identifiers, notifications, and behavioral/engagement summaries.
- Current checks shown in these routes are role-based, not school-scoped. A teacher role alone is not a least-privilege policy for a specific student population.

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
2. Decide the tenant model and authorization rules before editing ORM tables.
3. Implement tenant-aware migrations and explicit ownership backfill policy.
4. Add a reusable server-side school-scope dependency and apply it consistently to every endpoint and service query.
5. Add cross-tenant isolation tests, including negative tests for guessed IDs and parent/student-related records.
6. Separate demo/live analytics and include provenance/freshness.
7. Re-run the complete test suite and review migration behavior on a disposable database.
8. Only then conduct a formal privacy/security review and consider a controlled pilot.

## Existing safeguards worth preserving

- The orchestrator requires principal-level access, rejects unknown request fields, and declares human review required.
- The orchestration response explicitly says no autonomous action was taken.
- The specialist stages are deterministic Python functions; they should not be described as six independent autonomous LLM agents.
- The optional LLM summary should never override deterministic evidence or safety boundaries.

## Validation note

This document records static code observations only. It does not claim that the full test suite passed, that a penetration test was performed, or that the application is production-ready.
