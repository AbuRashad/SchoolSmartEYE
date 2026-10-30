# Multi-Agent AI Architecture

## Agent topology

The orchestrator coordinates six role-specific agents:

1. **Analytics** — interprets aggregate school metrics, patterns and data gaps.
2. **Safety** — reviews aggregate safety signals and identifies checks for staff.
3. **Academic** — interprets school-wide learning and attendance indicators and suggests supportive follow-up.
4. **Operations** — reviews operational reliability and service indicators.
5. **Evidence** — evaluates the sufficiency and consistency of the supplied aggregate evidence.
6. **Ethics Review** — receives the first five agents' structured analyses and reviews uncertainty, bias, privacy and unsupported claims.

When SCHOOLSMARTEYE_LLM_PROVIDER=ollama and OLLAMA_MODEL is configured, each stage is sent to the configured Ollama model with a distinct role instruction. The expected response is structured JSON containing a summary, observations, follow-up questions and risks. The ethics reviewer also receives the five prior agent analyses as a peer-review handoff.

## Privacy boundary

Only validated, allowlisted aggregate numeric metrics are sent to the model. The free-form API task, student identifiers, names, records and other unapproved fields are not sent. Do not add student-level fields to the provider payload.

## AI analysis versus deterministic guardrails

- analysis and advisory_summary are model-generated advisory content.
- flags, recommendations, warnings, evidence and unified findings are produced by deterministic application logic and remain authoritative.
- Each stage reports provider and analysis_status. A failed, missing or malformed model response is explicitly marked deterministic_fallback; it is not represented as a completed AI analysis.
- The report's ai_agent_count counts only stages that returned validated structured AI output.
- The ethics agent's deterministic review remains present even if the model is unavailable.

## Human oversight

All output requires qualified human review. Agents have no tools for taking operational actions, changing student records, contacting people or controlling school systems. requires_human_review remains true and autonomous_action_taken remains false.

## Configuration

Set these server-side environment variables:

- SCHOOLSMARTEYE_LLM_PROVIDER=ollama
- OLLAMA_MODEL=<your configured model>
- OLLAMA_BASE_URL=https://ollama.com (or a trusted Ollama-compatible endpoint)
- OLLAMA_API_KEY=<secret> when required by the provider

Keep API keys in deployment secrets or a local untracked .env file. Never commit credentials. If the provider is not configured or fails validation, the pipeline uses deterministic fallback.

## Validation

Run pytest -q. Tests cover role separation, structured output validation, provider failure fallback, privacy filtering, ethics handoff and the separation between AI advisory output and deterministic findings.
