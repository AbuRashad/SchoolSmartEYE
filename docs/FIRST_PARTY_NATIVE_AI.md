# SchoolSmartEYE First-Party Native Intelligence Engine

## Product principle

SchoolSmartEYE performs its core intelligence inside its own backend. It does not call Ollama, OpenAI-compatible endpoints, hosted LLMs, model marketplaces or third-party AI inference APIs. There is no cloud-first or cloud-fallback path.

## What the native engine does

The first-party engine is a school-domain expert system combining:
- allowlisted and range-checked aggregate metrics;
- explicit, inspectable school-domain thresholds;
- cross-signal consistency checks;
- six specialist reasoning roles (Analytics, Safety, Academic, Operations, Evidence and Ethics Review);
- structured peer review between specialist outputs;
- bounded explanations, questions and risk notes.

This is a domain-specific decision-intelligence engine, not a general-purpose generative language model. It must not be marketed as a foundation model or as having unrestricted language understanding. Its strength is transparent, testable reasoning over approved school indicators.

## External AI policy

External AI is disabled by design and is not part of the current runtime. A future external-assistance feature, if approved, must:
1. require an explicit request initiated by an authenticated Principal or authorized Head of Department;
2. show the exact data categories and destination before sending;
3. obtain confirmation for that individual request (no standing consent);
4. record requester, role, purpose, provider, data categories, timestamp and outcome in an immutable audit trail;
5. send only the minimum approved data and never student identifiers or individual records by default;
6. remain unavailable to teachers and ordinary background jobs.

No external call may be triggered by a scheduled task, a model fallback, an exception handler or a silent retry.

## Governance and safety

All outputs are advisory. Deterministic evidence and findings remain authoritative. No agent can discipline a student, notify a parent, change a record or initiate a physical intervention. Human review is mandatory. Small cohorts and rare events can still be sensitive even when metrics are aggregated.

## Extending the native engine

The next legitimate intelligence improvements should use first-party school data under institutional governance: longitudinal baselines, seasonality-aware anomaly detection, calibrated confidence, explicit data-quality scoring, and evaluation against expert-labelled historical cases. Do not train or claim a predictive model until representative, permissioned training/evaluation data and measured validation results exist.
