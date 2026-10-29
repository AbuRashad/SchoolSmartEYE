# Optional specialist-agent LLM runtime

The six specialist stages always produce deterministic findings and evidence. An optional Ollama chat call produces a separate advisory summary; it does not replace the deterministic summary or alter flags, recommendations, evidence, confidence, or trigger actions. The ethics-review stage receives the five preceding deterministic stage outputs and records which stages it cross-reviewed. If the provider is disabled, unconfigured, times out, returns invalid content, or errors, deterministic output remains available. Human review remains mandatory.

## Environment

Set these in the runtime environment or an untracked local `.env` file:

```dotenv
SCHOOLSMARTEYE_LLM_PROVIDER=deterministic
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_MODEL=
OLLAMA_API_KEY=
```

- Keep `SCHOOLSMARTEYE_LLM_PROVIDER=deterministic` to disable network calls.
- Set it to `ollama` and provide `OLLAMA_MODEL` to enable optional summaries.
- For Ollama Cloud, use the Cloud API base URL and API key from your Ollama account. For a self-hosted Ollama server, set `OLLAMA_BASE_URL` to that server and keep it private.
- Never commit real API keys or paste them into source code. The API key is sent only in the authorization header and is never logged.
- Provider requests contain only the specialist label and allowlisted, validated aggregate numeric metrics. The free-form task text is intentionally not sent to the model, because it could contain student identifiers or other sensitive details.
- Calls have a 12-second timeout and do not follow redirects. A provider failure falls back to deterministic output.

## Unified review report

The orchestration response includes a deterministic `report` containing flags, recommendations, and warnings labelled with their originating specialist, plus evidence count and explicit limitations. The report does not treat advisory LLM text as evidence and does not claim that aggregate metrics establish individual causes. Consumers should display the evidence and limitations alongside findings and keep the human-review gate.

## Limitations

This is bounded sequential orchestration, not a fully autonomous multi-agent framework. All six roles are invoked sequentially, and their deterministic findings remain authoritative. The current API obtains metrics from the existing analytics overview; confirm whether those values are live or demo/static before operational use. Tenant scoping, real-data provenance, and end-to-end deployment validation remain separate requirements.
