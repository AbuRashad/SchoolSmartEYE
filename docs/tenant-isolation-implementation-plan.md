# Tenant Isolation Implementation Plan

## Decision status

Proposed design for review. This document does not change application behavior or authorize production migration. Implement only after reviewing the data model, current API consumers, and existing data/backfill requirements.

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
