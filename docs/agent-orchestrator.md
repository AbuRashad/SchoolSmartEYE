# Agent Orchestrator v1

## What it does

`POST /api/v1/agent/orchestrate` runs six bounded specialist stages in order:

1. `analytics` — summarizes the validated aggregate metric set.
2. `safety` — flags aggregate signals that warrant human verification.
3. `academic` — offers school-level educational follow-up suggestions.
4. `operations` — checks selected operational indicators.
5. `evidence` — records the allowlisted aggregate metrics used as evidence.
6. `ethics_review` — reports limitations and reinforces the human-review requirement.

These are deterministic Python functions, not six independent autonomous AI agents. If the optional Ollama provider is explicitly enabled and configured, it may rewrite bounded stage summaries; deterministic flags, recommendations, and evidence remain authoritative.

## Access and data boundaries

- The endpoint requires a Principal or Ministry role through `require_principal`.
- The current analytics overview returns static/demo aggregate values. It is not a live, verified school data feed.
- The orchestrator accepts only an allowlist of finite numeric aggregate metrics within configured domain bounds. Unknown metrics, booleans, invalid numbers, out-of-range values, and fractional values for integer metrics are excluded.
- The request's free-form task text is not sent to the Ollama provider. The provider receives the specialist label and validated aggregate metrics only.
- If Ollama is enabled, aggregate metrics leave the application and are sent to the configured provider endpoint. Configure this only after reviewing provider terms, data residency, access controls, and institutional approval.
- The API rejects unknown request fields, requires human review, and takes no autonomous operational action.

## Current limitations — not production-ready for live multi-school data

- The analytics overview is demo/static data, not a verified live source.
- There is no tenant/school identifier in the current demo data model; tenant-level isolation is not implemented or tested.
- No claim is made that the stages are independent LLM agents or that live data is available.
- Role-based access is not a substitute for school-level data isolation.

Do not use this endpoint to make real student safety or academic decisions until live-source provenance, tenant boundaries, access control, data freshness, and end-to-end tests are implemented and reviewed.

## Test

Run from the repository root:

```bash
python -m pytest -q
```

The API regression test should assert all six stage names and verify that authentication, role restrictions, the human-review gate, no-autonomous-action contract, and rejection of unknown request fields remain enforced.

## Threat model

The current boundary reduces accidental PII propagation by filtering to validated aggregate numeric metrics and not forwarding free-form task text to the LLM provider. Remaining risks include stale/demo metrics, incorrect or misleading aggregates, provider data-handling terms when Ollama is enabled, role-hierarchy semantics, and absent tenant identifiers. Before adding live student data or enabling an external LLM for school use, require explicit authorization, a privacy review, tenant-isolation tests, validated output schemas, and source-data provenance checks.
