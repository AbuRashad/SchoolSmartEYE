# Parallel PostgreSQL database — implementation plan

## Decision

The next-generation database is a separate, initially empty PostgreSQL database. The current database remains the live application database and is not modified by this work.

## Isolation guarantees

- The legacy `Base`, `engine`, `SessionLocal`, `DATABASE_URL`, and Alembic stream remain unchanged.
- The new schema has independent SQLAlchemy metadata (`NextBase`), session factory, and Alembic stream.
- The application does not connect to the new database during startup. A connection is created only when explicitly requested through the next-generation session factory.
- No demo seeding, data copy, or automatic dual-write is implemented.
- PostgreSQL is required for the new database. The legacy database may continue using SQLite or its current configured backend.

## Initial domains

Organizations and schools; campuses; users and scoped memberships; students and guardians; classes and enrollments; attendance events; cameras and edge devices; camera telemetry; AI events; incidents and human reviews; provenance-aware metric observations; consent records; and audit events.

Tenant-owned tables carry both `organization_id` and `school_id`, with composite school/organization foreign keys to prevent cross-tenant school assignment. Ministry-level memberships can be organization-scoped with no school_id. Ministry reporting must be implemented as aggregate-only service queries; this schema alone does not grant access.

## Data classification rules

- Do not store raw video frames or image blobs in PostgreSQL; store controlled object-storage references only.
- Wearable/health measurements are intentionally not part of this first schema baseline. They require a separate privacy, consent, retention, and access review before introduction.
- AI detections are unverified observations until a human review or trusted validation workflow changes their status.
- Every metric records source and validation status; missing telemetry is not converted into fabricated values.
- Do not put student-identifiable physiological data in Ministry-facing aggregate views.

## Provision and migrate

1. Provision a new, empty PostgreSQL database with a dedicated least-privilege application/migration role.
2. Set `NEXT_DATABASE_URL` in the deployment secret store; never commit credentials.
3. Review SQL with `alembic -c alembic-next.ini upgrade head --sql`.
4. Apply schema only with `alembic -c alembic-next.ini upgrade head`.
5. Verify the database contains tables and zero business rows.
6. Build read/write services and tenant-isolation tests before any real data is entered.

Never set `NEXT_DATABASE_URL` to the current `DATABASE_URL`. No migration from the legacy database is authorized by this plan.

## Current limitations

This is a schema foundation, not a production cutover. It does not yet implement PostgreSQL row-level security, application-level authorization for the new tables, automated backups, retention jobs, first-admin provisioning, or integration of existing endpoints. Those are release gates before live student data is stored.
