# First-Party Native School Intelligence Engine

The six specialist roles run inside the SchoolSmartEYE backend. The engine does not call Ollama, cloud LLMs, OpenAI-compatible endpoints, model marketplaces or third-party AI inference APIs.

## What it is

This release is a domain-specific expert system, not a general-purpose foundation model. It combines allowlisted aggregate metrics, explicit school-domain thresholds, cross-signal consistency checks, six specialist roles, structured peer review, bounded explanations and follow-up questions. Its reasoning is inspectable and versioned with the application.

## External AI policy

External AI is not configured or called in this release. A future external-assistance workflow must require an explicit request from an authenticated Principal or authorized Head of Department, show the exact data and destination, obtain confirmation for that request, and record requester, role, purpose, destination, data categories, timestamp and outcome. It must never run as an automatic fallback or scheduled background action.

## Safety

Only approved aggregate indicators enter this engine. Outputs are advisory. Deterministic findings and evidence remain authoritative. No agent can change student records, discipline a student, notify parents or trigger a physical intervention. Human review is mandatory. Aggregated data can still be sensitive for small cohorts or rare events.

## Roadmap to stronger native intelligence

The next improvements should use institutionally approved first-party data: longitudinal baselines, seasonality-aware anomaly detection, data-quality scoring, calibrated confidence and evaluation against expert-labelled historical cases. Do not claim predictive accuracy until representative evaluation data and measured results exist.
