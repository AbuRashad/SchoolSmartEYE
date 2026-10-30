# Security Boundary Review — Demo Readiness

## Scope

This is a code-review snapshot of the current demo architecture, not a penetration test, compliance certification, or claim that every route has been exhaustively audited. Findings below are based on inspected ORM models, authentication dependencies, student/bracelet/zone/risk/agent endpoints, settings, and orchestration routes.

## Current status

**Do not connect real student records or use this build for live multi-school operations yet.** The branch now enforces school scope on several key routes, but substantial school-owned data paths and global in-memory services remain outside the tenant boundary.

## Update — first enforced school boundary

The current branch has a persisted `School` model and school ownership on users and students. Unit 15 agent snapshots and persisted feedback are now filtered by authenticated school for school accounts; Ministry retains cross-school read access. Student lists, profiles, behavioral history, bracelet lists, and zone lists are filtered by the authenticated user's school. Ministry accounts may read across schools on these routes. Student/bracelet mutations require an exact school-principal role; Ministry is also denied settings mutation, agent feedback submission, orchestration, and camera registration/control. Attendance-risk lists and individual risk/recommendation lookups now apply the caller's school scope. Agent feedback writes require a school staff account and a student in that same school. The school scope is derived from the authenticated user record, never from a client-supplied school ID. Student profile notifications are limited to records explicitly linked to the student because parent IDs are not tenant-safe in the current schema.

**Covered by regression tests:** school-specific student and zone lists; ministry cross-school student, bracelet, and zone reads; student profile visibility; cross-school student and bracelet mutation denial; school assignment on student creation; risk and recommendation scope; and Ministry denial for protected mutations.

**P0 remains open:** attendance and notifications need full schema-level tenant ownership; camera health/review, wearable reporting, SSI, reports, portal, dashboard, analytics, and remaining units/services need independent policy and scope review. Several agent summary/metrics/baseline reads still aggregate globally. Runtime settings are process-global: although Ministry can no longer patch them, a school principal's PATCH still changes shared process settings and must be redesigned as per-school settings before multi-tenant use. In-memory stores are not tenant-aware. This slice is not a claim of complete multi-tenant isolation or production readiness.

## Findings and priorities

### P0 — Establish school/tenant isolation before multi-school live data

- The ORM has a `School` tenant model; users and students carry school ownership, and bracelets inherit their school through the assigned student.
- Student lists, profiles, behavioral history, bracelet lists, and zone lists are school-filtered for school users; Ministry receives cross-school reads on those routes.
- Attendance risk and per-student agent recommendations enforce school scope. Agent feedback writes verify that the target student belongs to the caller's school.
- Ministry is blocked from student/bracelet writes, settings PATCH, agent feedback POST, orchestration POST, and camera registration/control. The generic role hierarchy still allows Ministry through some `require_teacher` / `require_principal` dependencies; each such route must be reviewed rather than assumed safe.
- Dashboard, SSI, reports, analytics, agent-wide summaries, cameras, wearable coverage/history, and other data services remain partially global, demo-only, or inaccessible to Ministry; none should be described as a complete Ministry all-schools read surface.
- Runtime settings are global process state. A school principal can still change those shared settings, so the PATCH endpoint is not tenant-isolated even though Ministry is denied.

**Required before live multi-school use:** add school ownership to attendance and notification records; finish school-scope filtering for all student-specific reads; define an explicit Ministry all-school read API for camera, wearable, safety, dashboard, and reporting data; reject Ministry on every mutation endpoint (including less-obvious POST actions); replace process-global settings with per-school configuration; and add cross-tenant denial tests across all services. Do not infer tenant identity from client-supplied IDs alone.

### P1 — Replace demo analytics with a provenance-aware data source

- `GET /analytics/overview` currently returns hard-coded illustrative metrics, including attendance, incidents, camera activity, and compliance.
- The orchestrator consumes this overview. As a result, a successful response is not evidence of live school conditions.

**Required:** make demo/live mode explicit in the API and UI; label all demo metrics visibly; include source and freshness metadata for live metrics; reject or clearly flag stale/missing inputs; and test that demo values cannot be mistaken for live observations.

### P1 — Review student-sensitive endpoint exposure

- Student profiles can include attendance, last-seen zone, bracelet details, parent identifiers, notifications, and behavioral/engagement summaries.
- Student profile and behavioral-history routes now resolve the student within the caller's school; Ministry may read across schools. Parent-linked notifications are intentionally omitted unless explicitly linked to the student because parent IDs are not yet tenant-scoped.
- Agent-wide insights, feedback metrics, and baseline summaries now apply school-aware filtering to registered student IDs; the underlying snapshots are still in-memory demo data and must be replaced with durable school-owned records before production. The current `require_teacher` hierarchy is not itself a tenant boundary.

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
4. Extend the reusable server-side school-scope dependency to every endpoint and service query; create explicit cross-school read-only Ministry dependencies.
5. Add cross-tenant isolation tests, including negative tests for guessed IDs and parent/student-related records.
6. Separate demo/live analytics and include provenance/freshness.
7. Re-run the complete test suite and review migration behavior on a disposable database.
8. Only then conduct a formal privacy/security review and consider a controlled pilot.

## Existing safeguards worth preserving

- The orchestrator requires an exact school-principal role, rejects unknown request fields, and declares human review required.
- The orchestration response explicitly says no autonomous action was taken.
- The specialist stages are deterministic Python functions; they should not be described as six independent autonomous LLM agents.
- Model-generated advisory analysis must never override deterministic evidence or safety boundaries.

## Validation note

This document records static code observations only. It does not claim that the full test suite passed, that a penetration test was performed, or that the application is production-ready.
