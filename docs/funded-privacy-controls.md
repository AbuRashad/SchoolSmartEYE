# Funded privacy controls: erasure, bracelet retention, and local AI

This implementation adds code paths and automated tests for three funded requirements.

## 1. Student erasure

`DELETE /api/v1/students/{student_id}` is now a destructive erasure operation, not a simple ORM row deletion.

- Requires the explicit `MANAGE_RETENTION_POLICY` governance permission and an authenticated school membership.
- Deletes the student row and structured student-linked records: attendance, notifications, feedback records, bracelet assignment/readings, parent-student links, and pending parent invitations.
- Removes matching Unit 15 engagement snapshots from the in-memory store.
- Rewrites `agent_performance.jsonl` to remove matching feedback records. Malformed JSONL causes the operation to stop rather than silently claim success.
- Writes a privacy-preserving audit record with the school, actor, timestamp, and per-store deletion counts. The audit schema deliberately has no student identifier.

**Scope boundary:** the current application has no student-to-video-file index, and it cannot identify a student's appearance inside unindexed CCTV footage. External backups, database snapshots, exported files, and third-party copies are also outside this endpoint's control. Those stores need their own retention/erasure procedures before the organisation can claim end-to-end erasure across all systems. The 72-hour video TTL remains a separate control.

## 2. Bracelet readings — 30 days

- Every successful bracelet ping now writes a timestamped `BraceletReading` row.
- `GET /api/v1/bracelets/{bracelet_id}/readings` accepts only a 1–30 day query window and is school-scoped.
- Readings older than `BRACELET_READING_RETENTION_DAYS` (default 30) are hard-deleted at startup, hourly by a background task, and opportunistically during new pings.
- `Bracelet.last_seen_at` remains the current operational status field; the 30-day policy applies to the timestamped history table.

The new table starts empty at migration time. The current schema had no persisted bracelet history table to backfill or purge.

## 3. Local Ollama configuration

The settings are now first-class fields in `app/core/config.py`:

```dotenv
SCHOOLSMARTEYE_LLM_PROVIDER=deterministic
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=
OLLAMA_API_KEY=
OLLAMA_TIMEOUT_SECONDS=12
```

- Deterministic remains the default; Ollama is opt-in.
- Local host default is `127.0.0.1:11434`.
- Docker Desktop can usually reach the host service through `host.docker.internal`; the Ollama listener and firewall must be configured securely.
- The provider still receives only allowlisted aggregate numeric metrics and optional bounded peer analysis, never free-form task text or student identifiers.
- Missing model, connection failure, timeout, or invalid response falls back to deterministic results.

## Migration and rollout

Alembic revision `0008` creates `bracelet_readings` and `student_erasure_audits`. Apply it with the normal reviewed deployment process; this PR does not migrate production or deploy the application.

## Verification targets

- Erasure tests verify deletion across each structured store, in-memory snapshots, and feedback JSONL, plus a non-identifying audit.
- Retention tests verify the 30-day cutoff, ping persistence, and bounded history reads.
- Migration smoke tests verify the new tables and confirm the audit has no `student_id` column.
- Ollama configuration tests verify the local endpoint and deterministic default.
