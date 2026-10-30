# Lesson Analysis and Two-Stage Approval Workflow

## Product decision

Lesson data is analysed immediately after teacher submission. The analysis is advisory and visible to the assigned Head of Department (HOD) during the first review. The principal performs the final approval only after HOD approval.

The analysis engine must never approve a lesson or change its governance status.

## Workflow

1. Teacher submission — a teacher submits a lesson record and evidence metadata. The server derives teacher and school from the authenticated account; clients cannot set approval state, verification state, school ownership, or submitter identity.
2. Immediate native analysis — the deterministic native engine runs against the submitted lesson data and produces a versioned, timestamped analysis snapshot. The snapshot is preliminary/unverified and is not approved evidence.
3. HOD review — only the HOD assigned to that department and school can see the review queue and decide on those lessons. An HOD cannot approve their own submission. The HOD sees the original submission plus preliminary findings, limitations, and recommendations.
4. Principal review — only the school's principal can decide after HOD approval. The principal sees the submission, analysis snapshot, and HOD decision.
5. Final state — only principal approval sets the lesson to approved. Only then may the lesson be used as verified evidence or a trusted learning baseline.

## State machine

- pending_hod: teacher submitted; preliminary analysis exists; waiting for HOD.
- pending_principal: HOD approved; waiting for principal.
- approved: HOD and principal approved in order.
- rejected_by_hod / rejected_by_principal: returned to teacher for correction.

A corrected resubmission starts a new approval round. Prior decisions and analysis snapshots remain immutable history. The new submission is analysed again before the next HOD review.

## Proposed data model

Do not overload AggregateObservation: it represents school-level numeric aggregates, not individual lessons.

- Department: id, school_id, name, stable department code.
- LessonSubmission: id, school_id, department_id, teacher_user_id, lesson date, class/grade identifiers where appropriate, structured lesson payload, submission version, workflow state, current approval round, timestamps.
- LessonAnalysisSnapshot: id, lesson_submission_id, engine/version, status preliminary_unverified, structured findings/recommendations, input digest, created timestamp. Snapshots are immutable.
- LessonApprovalDecision: append-only history with lesson id, round, stage hod/principal, decision approved/rejected, actor, reason, timestamp.
- User.department_id for HOD assignment; HOD role must be school-scoped and department-scoped.

Use foreign keys and indexes for school, department, teacher, workflow state, lesson, and decision history. Enforce unique department code within a school. Do not infer department from free-text subject at authorization time.

## Authorization invariants

- Teacher submits only under authenticated school_id and assigned department; server supplies teacher_user_id.
- HOD must have role hod, matching school_id, and matching department_id.
- HOD cannot decide on a submission they created.
- Principal must have role principal and matching school_id.
- Principal approval is rejected unless the current round has an HOD approval.
- Ministry access does not implicitly grant school-level approval authority.
- Every decision and resubmission is written to append-only governance audit in the same transaction as the state change.
- Rejection reason is mandatory; approval may include a note.
- Concurrent decisions must use transaction/row locking or compare-and-set state checks.

## Analysis and learning boundaries

- Run the native deterministic engine immediately after a valid teacher submission.
- Store output as a preliminary snapshot; display engine version and analysis timestamp to reviewers.
- Rejection or correction creates a new snapshot; never overwrite old analysis or approval history.
- The engine may provide risk flags, missing-evidence warnings, trend context, and recommendations, but must not autonomously grade a teacher, issue sanctions, or approve data.
- Only records in approved state after both stages may enter verified evidence sets or trusted learning baselines.
- Preliminary and rejected records may be used only for explicitly labelled provisional review and must be excluded from trusted training/baseline inputs.
- The current engine is deterministic/rule-based; describe it as native analysis, not a trained ML model.

## Proposed API surface

- POST /lessons — authenticated teacher submission; runs native analysis; creates pending_hod.
- GET /lessons/hod-queue — assigned HOD department queue, with preliminary analysis.
- POST /lessons/{id}/hod-decision — HOD approve/reject with reason.
- GET /lessons/principal-queue — principal school queue after HOD approval.
- POST /lessons/{id}/principal-decision — final principal approve/reject.
- GET /lessons/{id} — role- and scope-filtered submission, snapshots, and decision history.

All payloads use strict schemas (extra=forbid). Client-supplied workflow status, school, submitter, actor, verification, and analysis output are forbidden.

## Migration and test requirements

Implement in a new Alembic revision after 0004; never rewrite existing migrations. Test:
- teacher cannot submit into another school/department;
- HOD sees only assigned department;
- HOD cannot approve own submission or another department's lesson;
- HOD approval makes lesson visible to principal queue;
- principal cannot skip HOD;
- only principal approval produces approved;
- rejection requires a reason and correction starts a new round;
- prior decisions and analysis snapshots remain immutable;
- audit records are atomic with each transition;
- engine runs on submission and HOD sees the same persisted preliminary snapshot;
- unapproved/rejected lessons never enter verified learning inputs.

## Current repository gap

The existing AggregateObservation model and /observations endpoints handle school-level aggregate metrics only. The repository does not yet contain a lesson-submission model, department model/assignment, teacher lesson-ingestion endpoint, or lesson-specific analysis snapshot. Implementing lesson workflow by attaching department approvals to aggregate metrics would conflate different data domains and create unsafe authorization semantics.