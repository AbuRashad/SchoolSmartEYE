# Security Boundary Review — Demo Readiness

## Scope

This is a code-review snapshot of the current demo architecture, not a penetration test, compliance certification, or claim that every route has been exhaustively audited. Findings below are based on the current ORM models, authentication dependencies, student/bracelet endpoints, analytics overview, and orchestrator documentation.

## Current status

**Do not connect real student records or use this build for live multi-school operations yet.** The current code demonstrates role-based access and several bounded agent safeguards, but it does not yet establish school-level data isolation.

## Findings and priorities

### P0 — Establish school/tenant isolation before multi-school live data

- The ORM `User` model has no school/tenant association. The `Student` model and related records also have no school identifier.
- `GET /students` queries all student rows and relies on the teacher-role dependency; `GET /students/{student_id}/profile` and behavioral history look up records by student ID without a school boundary.
- Bracelet endpoints list or resolve bracelet records by ID and role, without a tenant boundary.
- Role-based authorization answers what role a user has; it does not prove which school's records that user may access.

**Required before live multi-school use:** define a canonical School/Tenant model; map each user to an explicitly authorized school scope; add tenant ownership or validated tenant relationships to school-owned data; apply scope filters to every read/write path; and add cross-tenant denial tests for list, detail, create, update, delete, attendance, bracelet, notification, incident, and analytics paths. Do not infer tenant identity from client-supplied IDs alone.

### P1 — Replace demo analytics with a provenance-aware data source

- `GET /analytics/overview` currently returns hard-coded illustrative metrics, including attendance, incidents, camera activity, and compliance.
- The orchestrator consumes this overview. As a result, a successful response is not evidence of live school conditions.

**Required:** make demo/live mode explicit in the API and UI; label all demo metrics visibly; include source and freshness metadata for live metrics; reject or clearly flag stale/missing inputs; and test that demo values cannot be mistaken for live observations.

### P1 — Review student-sensitive endpoint exposure

- Student profiles can include attendance, last-seen zone, bracelet details, parent identifiers, notifications, and behavioral/engagement summaries.
- Current checks shown in these routes are role-based, not school-scoped. A teacher role alone is not a least-privilege policy for a specific student population.

**Required:** define per-school and, where applicable, class/student-level authorization; minimize returned fields by role and purpose; audit access to behavioral history and location-related data; and verify authorization failures with tests.

### P1 — Keep external model use privacy-reviewed

- The hybrid model path can send validated aggregate metrics to a configured cloud provider; free-form task text and student identifiers are not forwarded.
- Aggregate metrics may still be sensitive when small cohorts or rare incidents are involved. “Aggregate” does not automatically mean anonymous.

**Required:** require institutional approval before enabling external providers; document endpoint, retention, residency, and access controls; minimize metrics; and test that identifiers and free-form task text never reach any provider. The local inference endpoint should remain on a trusted private network.

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
- Model-generated advisory analysis must never override deterministic evidence or safety boundaries.

## Validation note

This document records static code observations only. It does not claim that the full test suite passed, that a penetration test was performed, or that the application is production-ready.
