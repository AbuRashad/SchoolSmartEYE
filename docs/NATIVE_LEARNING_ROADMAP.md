# SchoolSmartEYE — Native Learning Roadmap

## Current first iteration

The native intelligence engine is a deterministic, first-party expert system. The
native learning module adds an explainable statistical baseline primitive using
the median and median absolute deviation (MAD).

This is **not yet a trained machine-learning model** and does not establish
predictive accuracy. It only assesses whether one approved aggregate metric
deviates from a supplied historical series.

## Data trust classes

- `demo`: synthetic or illustrative values. Use for UI, pipeline and test
  validation only. Never mix these observations into a live-school baseline.
- `live_unverified`: received from a configured source but not yet validated.
  Quarantine from learning and operational alerts.
- `live_verified`: source, timestamp, metric definition, scope and quality
  checks have passed. Eligible for approved aggregate baseline calculations.

Every future ingestion record should carry provenance, observation time,
metric definition/version, school scope, source identifier, validation state
and an explicit demo/live classification.

## Initial anomaly method

For each metric, collect a historical window and calculate:

- baseline = historical median
- MAD = median absolute deviation from that median
- modified z-score = 0.6745 × (current − median) / MAD

The first version requires at least seven valid historical observations.
When MAD is zero, it does not label a value an anomaly; it emits a
human-review state instead. Thresholds are configurable only through reviewed
code/configuration, not arbitrary client input.

This method is a screening signal, not a diagnosis or causal explanation.
Seasonality, holidays, timetable changes, source outages and metric-definition
changes must be considered before operational use.

## Next engineering stages

1. Add a persistent, append-only aggregate observation table with provenance
   and validation state; do not store student names, IDs, free-text notes,
   images or raw video in this learning store.
2. Add a principal-authorized ingestion endpoint with strict metric allowlists,
   bounds, timestamps, idempotency and audit logging.
3. Build a controlled import from existing aggregate history. Preserve demo
   labels and exclude demo rows from live baselines.
4. Add data-quality checks, per-school scope isolation and retention controls.
5. Add time-aware baselines and seasonality only after enough verified history
   exists.
6. Evaluate candidate models on time-separated historical data and human-
   reviewed outcomes before enabling any predictive claim.

## Governance requirements

- No external AI/LLM inference, cloud model fallback or hidden provider calls.
- No automatic school action. Findings remain advisory and require authorized
  human review.
- No cross-school learning unless explicitly authorized, anonymized, governed
  and technically isolated.
- Do not train on individual student profiles or sensitive attributes in this
  initial phase.
- Keep demo and verified live datasets separate in storage, evaluation and UI.
