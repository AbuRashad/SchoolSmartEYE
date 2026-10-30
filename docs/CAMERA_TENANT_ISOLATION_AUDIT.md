# Camera Tenant Isolation Audit

Audit date: 2026-10-30
Branch: `feat/native-school-intelligence-engine`

## Executive finding

Camera review persistence must remain blocked until camera ownership is represented consistently across both the database-backed inventory and the live ingestion registry. The current implementation has a database camera inventory, but the live REST endpoints operate on a process-wide in-memory ingestion service. Adding only `school_id` to SQL rows would not scope those live operations.

## Confirmed findings

### Authentication and roles

- `app/api/deps.py` resolves the user from the JWT subject against the database; callers cannot choose the authenticated user ID.
- Role hierarchy is teacher < principal < ministry. `require_principal` permits Ministry because it is a minimum-scope hierarchy check.
- School-operated observation ingestion explicitly narrows access to `user.role == "principal"` and requires `user.school_id`.
- There is no dedicated school-manager role. The review feature should initially follow the explicit principal-only pattern unless product policy authorizes a distinct role.
- The login response's `UserOut` omits `school_id`; this is not a blocker for server-side scoping, but client display/context may need a deliberate, non-authoritative school label.

### Database ownership gaps

- `User.school_id` exists.
- `Zone`, `Camera`, and `Incident` have no `school_id`.
- `Camera.zone_id` references `Zone.zone_id`, but there is no database constraint proving that a camera and its zone belong to the same school because neither currently has tenant ownership.
- Existing demo seed functions create zones, cameras, and incidents without tenant assignment.
- `GovernanceAuditEvent` and the school-scoped audit listing for observations already exist. The audit model's docstring says append-only, but the schema alone does not enforce immutability.

### Live camera API / ingestion gap

- `app/api/v1/endpoints/cameras.py` uses a process-wide `ingestion_service` registry.
- Camera list, register, unregister, start, stop, snapshot, and MJPEG stream operations are keyed by camera ID only; they do not resolve a persisted camera row or verify its school against the authenticated user.
- Registration accepts a caller-supplied `zone_id` and does not validate that the zone belongs to the principal's school.
- Camera list response includes `source_url` for principal-or-higher roles. Since source URLs may contain credentials, the long-term API should return a redacted connection descriptor, not the secret-bearing URL, even to principals.
- Stream access currently uses role-level access but has no tenant-level camera ownership check. The MJPEG query-token compatibility path does not change this ownership gap.

## Required safe implementation plan

1. **Make camera registry ownership explicit**
   - Persist camera configuration and its school ownership.
   - Treat the in-memory ingestion service as a worker/runtime cache, not the source of authorization truth.
   - Every live operation must first resolve a persisted camera record scoped to the authenticated user's school.
   - Store connection secrets separately from public camera metadata; never return RTSP credentials in API responses.

2. **Tenant-scope relational inventory**
   - Add `school_id` to `zones`, `cameras`, and `incidents`.
   - Backfill the initial demo records to `school-primary` only after confirming the deployed data represents that school.
   - Add composite uniqueness and foreign-key constraints to guarantee camera-zone school consistency.
   - Update seed functions and every query/mutation using these models.

3. **Harden all camera endpoints**
   - Replace role-only camera access with authenticated user + school-scoped camera lookup.
   - Enforce principal-only management explicitly; teacher stream access may remain read-only only within the same school.
   - Apply the same check to list, register, delete, start, stop, snapshot, and MJPEG stream.
   - Do not rely on unguessable camera IDs as authorization.

4. **Then implement persistent review**
   - Candidate event must carry trusted school/camera/zone provenance from the persisted camera registry.
   - Reviewer identity comes only from the authenticated user.
   - Persist review decision and audit event atomically.
   - Keep decisions immutable; corrections become new review records.

## Required security tests

- School A principal cannot list, read, start, stop, delete, or stream School B camera.
- Teacher cannot register or manage cameras.
- Ministry cannot manage a school camera through inherited role hierarchy unless an explicit cross-school policy is approved.
- Caller-supplied school ID, reviewer ID, or zone ID cannot override authenticated scope.
- Camera and zone from different schools cannot be linked.
- Camera registration cannot expose or echo credential-bearing source URLs.
- Audit event and review record commit or roll back together.

## Decision

Do not add the review database table or review API yet. First refactor camera inventory/ingestion authorization around persisted school-owned camera records. This avoids a false sense of tenant isolation from a migration that does not protect the actual live camera endpoints.
