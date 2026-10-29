# Agent Orchestrator v1

## What it does
`POST /api/v1/agent/orchestrate` coordinates four bounded stages: analytics, safety, education, and ethics review. It is an initial deterministic orchestration layer, not a claim that four independent LLM agents exist.

## Access and data boundaries
- Requires an authenticated Principal or Ministry role through the existing `require_principal` dependency.
- Uses the existing analytics overview only; that endpoint currently returns static/demo aggregate values.
- The orchestrator copies only an explicit allowlist of numeric aggregate metrics into evidence. Student names, IDs, nested objects, strings, and other non-allowlisted values are excluded.
- Does not query student tables, send data to external model providers, access secrets, or take autonomous actions.
- Every result requires human review; safety flags are prompts to verify source reports, not findings about individuals.

## Current limitations
- The analytics overview is demo/static data, not a verified live data source.
- All stages are deterministic functions, not autonomous agents or LLM calls.
- No provider fallback, model call, or live availability is claimed.
- Tenant/school-level scoping is not represented in the current SQLite demo data model. Do not treat this endpoint as production-ready for multi-school live data until tenant boundaries are modeled and tested.

## Test
Run from the repository root:
`pytest -q tests/test_agent_orchestrator.py`

## Threat model
The endpoint assumes authenticated role claims resolved by the existing server dependency. Request input is bounded and rejects extra fields. Aggregate evidence is allowlisted and type-checked to reduce accidental PII propagation. Remaining risks include stale/demo metrics, role hierarchy semantics, and the absence of tenant identifiers in the current demo schema. Do not add live student data or LLM providers without explicit authorization, a privacy review, tenant-isolation tests, and validated output schemas.
