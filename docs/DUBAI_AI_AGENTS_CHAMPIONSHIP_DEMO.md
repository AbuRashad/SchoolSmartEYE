# Dubai AI Agents Championship — SchoolSmartEYE Demo

## Purpose

This is a competition demonstration of the existing SchoolSmartEYE specialist-agent orchestration. It uses synthetic school-wide aggregate metrics and does not access a real school database or student records.

## Run the demo

From the repository root:

```bash
python scripts/demo_competition_agents.py
```

To print the complete structured response:

```bash
python scripts/demo_competition_agents.py --json
```

The default configuration uses deterministic specialist logic. It is designed to run without a paid model or external AI service.

## Optional AI-assisted mode

The six specialist roles can request separate, role-specific JSON analyses from the configured Ollama-compatible endpoint. The ethics reviewer receives the earlier specialist analyses for cross-review. Deterministic findings and evidence remain authoritative; generated analyses are advisory.

PowerShell example (use a model and endpoint already available to you):

```powershell
$env:SCHOOLSMARTEYE_LLM_PROVIDER = "ollama"
$env:OLLAMA_MODEL = "your-available-model"
$env:OLLAMA_BASE_URL = "http://localhost:11434"
python scripts/demo_competition_agents.py
```

Do not commit API keys or secrets. If an authenticated endpoint is used, set `OLLAMA_API_KEY` in the local environment only. Review provider terms, data residency, and institutional approval before sending any school data to a remote endpoint. This demo itself uses synthetic values.

To return to deterministic mode:

```powershell
Remove-Item Env:SCHOOLSMARTEYE_LLM_PROVIDER -ErrorAction SilentlyContinue
```

## Demonstration scenario

The synthetic scenario intentionally combines several weak school-wide signals:

- Attendance rate: 87.5%
- Incidents today: 2
- Aggregate crowd-density indicator: 0.81
- Service uptime: 98.6%
- Other synthetic operational and governance metrics

The orchestrator runs these six specialist stages in sequence:

1. **Analytics** — reviews the validated aggregate metric set.
2. **Safety** — flags signals that warrant staff verification.
3. **Academic** — proposes supportive, non-punitive educational follow-up.
4. **Operations** — reviews service and operational indicators.
5. **Evidence** — identifies the validated aggregate evidence supplied to the review.
6. **Ethics Review** — cross-reviews the first five stages, uncertainty, evidence gaps, privacy boundaries, and the need for human oversight.

The unified response reports the stages, evidence, findings, provenance notice, limitations, provider status, and whether AI-assisted analysis completed or fell back to deterministic output.

## What this demo proves

- Six named specialist stages are coordinated by one orchestrator.
- Each optional AI analysis has a distinct specialist role and a strict structured-output schema.
- The ethics reviewer receives prior specialist analyses as a peer-review handoff.
- Only allowlisted, bounded aggregate numeric metrics are sent to the model; free-form task text and student-level identifiers are not sent.
- Model output is advisory. It cannot replace deterministic findings or evidence.
- Provider failure or invalid model output falls back to deterministic results.
- The response explicitly requires human review and records that no autonomous action was taken.

## Important limitations — be precise in the competition

This is a working multi-agent analysis prototype, not yet an autonomous school operations agent that executes external tools or performs real-world actions. The current demo does not connect to live camera streams, live external school systems, or production telemetry. Its input is synthetic data, and it creates no alerts, messages, tickets, or interventions.

The authenticated API obtains its aggregate analytics through the school-scoped analytics service. Non-demo tenant data is marked with unknown source provenance until record-level source verification is completed. Do not describe unknown-provenance records as verified live data.

## Recommended live-demo narration

"One school-wide request enters the orchestrator. It validates the available aggregate evidence, delegates analysis to six specialist roles, and passes the first five outputs to an ethics reviewer. The system then returns a traceable report with source limitations and a human-review gate. If the model is unavailable, the deterministic specialists still produce a bounded result. In this version, the system does not take an operational action without a future, explicitly approved action workflow."



## Human-approved action workflow (v1)

The branch also adds a persistent, school-scoped internal review-task workflow. It is deliberately limited to four server-defined action types:

- `review_attendance_trend`
- `review_safety_signals`
- `review_operational_readiness`
- `verify_evidence_quality`

A Principal/Ministry-authorised user can propose one of these tasks against an orchestration `request_id`. The proposal remains `pending_approval`. A different authorised user must approve it; approval creates an `open` internal task. A reviewer can reject it, and an open task can later be marked `completed`. The API lists only tasks in the authenticated user's resolved school.

API routes (under the configured API v1 prefix):

- `POST /agent/actions` — propose a predefined task
- `GET /agent/actions` — list this school's tasks
- `POST /agent/actions/{action_id}/approve` — independent approval
- `POST /agent/actions/{action_id}/reject` — reject a pending proposal
- `POST /agent/actions/{action_id}/complete` — complete an approved task

The request accepts only a UUID source request ID and an allowlisted action kind; callers cannot supply arbitrary task text or executable commands. The database stores no student identifier or student-level payload in this workflow. It does not send notifications, message parents, alter attendance, or control cameras. Those integrations require separate explicit permissions, audit design, and human approval gates.

Apply the schema migration before enabling this API on an existing database:

```bash
alembic upgrade head
```
