# Aggregate observation ingestion (phase 1)

- The first deployment provisions one school: `school-primary`.
- Principal accounts are assigned to that school by the server; request payloads cannot choose a school.
- The schema is tenant-ready: each observation has a school foreign key and the idempotency constraint is scoped to that school.
- Only allowlisted school-level aggregate metrics are accepted. Student IDs, names, free-text notes, images and video are not accepted.
- The API sets `data_status=live_unverified` and `validation_status=pending`; clients cannot submit either field.
- Duplicate submissions with the same school/idempotency key return HTTP 409.
- This endpoint stores observations only. It does not mark data verified, train a model, or trigger background AI.
- Before learning integration, add a separate audited verification workflow and enforce a reviewed source registry.
- Existing seed/demo data is not imported into this table and must not be used as a live baseline.
