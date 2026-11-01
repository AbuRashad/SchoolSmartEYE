# Native Hybrid AI Engine

SchoolSmartEYE uses a provider-independent runtime for its six specialist agents:
Analytics, Safety, Academic, Operations, Evidence and Ethics Review.

## Provider strategy

- `AI_PROVIDER=hybrid`: try the configured cloud model first, then the local model.
- `AI_PROVIDER=cloud`: use only the configured cloud endpoint.
- `AI_PROVIDER=local`: use only the configured local endpoint.
- `AI_PROVIDER=deterministic`: disable model calls and use deterministic application logic only.

Both endpoints must expose an OpenAI-compatible `POST /chat/completions` route. The cloud base URL must use HTTPS. A local endpoint may use HTTP when bound to a trusted private host. A typical local runtime is llama.cpp server; the application does not install or manage model weights or the inference server.

## Configuration

Set the following in the untracked `.env` file or deployment secret store:

- `AI_PROVIDER=hybrid`
- `AI_CLOUD_BASE_URL=https://provider.example/v1`
- `AI_CLOUD_MODEL=<model-id>`
- `AI_CLOUD_API_KEY=<secret>` (when required by the endpoint)
- `AI_LOCAL_BASE_URL=http://host.docker.internal:8081/v1` when the local inference server runs on the Docker host
- `AI_LOCAL_MODEL=<local-model-id>`
- `AI_LOCAL_API_KEY=<secret>` only if the local server requires it
- `AI_REQUEST_TIMEOUT_SECONDS=45`

Cloud model access, free tiers, quotas and pricing depend on the selected provider and may change. This code does not imply that a free cloud endpoint is provisioned. With no configured, reachable provider, the system remains in deterministic fallback mode.

## Privacy and safety boundary

Only allowlisted, finite, bounded aggregate numeric metrics are sent to a model. Free-form task text, student identifiers, names, individual records, camera frames and other unapproved fields are not included in provider payloads. The ethics agent receives only the first five agents' validated structured analyses. Do not add student-level data to the provider contract.

Model output must be valid JSON with exactly four fields: `summary`, `observations`, `follow_up_questions` and `risks`. Oversized, malformed or unexpected output is rejected. Model output is advisory only; deterministic findings, evidence and guardrails remain authoritative. Every report requires human review and no agent can take an autonomous action.

## Operational notes

- The backend does not download model weights or start a local inference server.
- In Docker, `host.docker.internal` is mapped to the host gateway for local inference access.
- Keep API keys out of source control and logs. The runtime never returns credentials in its status payload.
- Verify provider availability and model suitability in the deployment environment before claiming live AI analysis.
