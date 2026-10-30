# Camera Review Persistence Readiness

## Status

Design assessment only. This document does not enable camera review persistence, expose a review API, or claim production readiness.

## Existing repository facts

- `User.school_id` exists and is nullable.
- Current application roles are `teacher`, `principal`, and `ministry`; there is no distinct `school_manager` role.
- The current authorization dependency resolves the authenticated user from the database and supports role checks.
- `GovernanceAuditEvent` already exists with school, actor, event type, target, JSON details, and timestamp fields.
- `Camera`, `Zone`, and `Incident` currently do not carry a `school_id`.
- The camera review workflow currently creates an in-memory domain record only. It is not a persisted queue and its reviewer ID is not authentication proof.

## Blocking integrity issue

A principal's `school_id` cannot securely scope a camera review while the camera and zone records have no tenant ownership. A review record that merely accepts a caller-supplied school ID would allow cross-school association and is not acceptable.

The existing audit table is useful infrastructure, but its presence alone does not make writes append-only. Append-only behavior must be enforced by application permissions and database policy/trigger where supported, and audit rows must be written in the same transaction as the governed review decision.

## Required implementation sequence

1. **Resolve role policy**
   - Decide whether `principal` is the authorized school manager role for phase one, or whether a separate `school_manager` role is required.
   - Do not silently broaden existing role permissions.
   - Ministry-wide access must remain a separate explicit policy; a school review queue should not become globally readable by default.

2. **Establish tenant ownership**
   - Add `school_id` foreign keys to `zones` and `cameras` (and to `incidents` if they are to participate in the same tenant-scoped operational workflow).
   - Backfill the existing single-school demo records to the provisioned school only after verifying the deployment's actual data ownership.
   - Add indexes and constraints. Prefer composite uniqueness/foreign-key patterns where needed to ensure a camera's zone belongs to the same school.
   - Update seed data and all relevant queries to apply tenant scope from the authenticated user, never from request payloads.

3. **Persist review records**
   - Add a review table with a generated review ID, school ID, event ID, camera ID, zone ID, decision, authenticated reviewer user ID, review timestamp, and rationale.
   - Store only event metadata and necessary evidence references; never persist raw frame pixels or temporary tracker IDs in this workflow.
   - Enforce valid decisions and immutable review history. A later correction should be a new review/audit event, not an overwrite of the prior decision.
   - Add indexes for school, event, decision, and review timestamp. Add idempotency/concurrency protection for duplicate submissions as appropriate.

4. **Expose an authenticated API**
   - Derive actor identity from `get_current_user`; do not accept `reviewer_user_id` or `school_id` as trusted request fields.
   - Require the explicitly approved school-manager role.
   - Verify the camera and zone belong to the authenticated user's school and that the candidate event references that same camera/zone.
   - Return no cross-tenant existence information; use a consistent not-found/forbidden policy.
   - Write the review row and `GovernanceAuditEvent` in one database transaction.

5. **Validate**
   - Migration upgrade/downgrade against the supported database.
   - Cross-school read and write denial tests.
   - Teacher/ministry/unauthenticated authorization tests.
   - Forged actor ID and forged school ID tests.
   - Camera-zone-school consistency tests.
   - Audit atomicity, immutability, duplicate submission, and concurrent review tests.
   - Confirm API responses omit frame pixels, credentials, and temporary tracker IDs.

## Safe next implementation slice

The next code change should be the tenant ownership migration and corresponding model/query updates, not the review queue itself. Once camera and zone ownership is enforceable, the persistent review queue and API can be implemented without inventing tenant boundaries.

## Current limitations

- No real school cameras are available for validation yet.
- No detector model has been validated against representative school footage.
- Synthetic fixtures test software contracts only; they do not establish camera accuracy or operational readiness.
- This assessment does not certify the existing application as fully tenant-isolated. Other existing tables and endpoints still require a separate tenant-scope audit.
