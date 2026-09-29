# Research evidence store

These directories are repository-local governance artifacts.

- `acquisitions/` immutable Massive MCP acquisition manifests and source provenance
- `registry/` preregistered hypotheses
- `runs/` daily run manifests and data-quality summaries
- `validations/` independent statistical-validator reports
- `audits/` candidate or daily-run methodology-auditor reports
- `forecasts/` immutable forecast-time records
- `outcomes/` later realized outcomes / OOS scoring records bound to forecast digests
- `promotions/` immutable successful promotion records

A transient Massive MCP workspace is not a substitute for durable evidence. Preserve the sealed acquisition manifest and downstream deterministic artifacts before a governed run is considered complete.

Preserve rejected, inconclusive, and invalid evidence outside `promotions/`; do not delete it merely because a candidate failed.


## Daily attempt layout (v0.3.1)

Use one stable daily `run_id` and a unique `attempt_id` for each retry. Runtime artifacts are generated locally and are intentionally not shipped in release packages. `research/data/<attempt_id>/` contains immutable materialized MCP JSONL + metadata; `research/pipeline/<attempt_id>/` contains deterministic daily outputs; acquisition, handoff, audit, forecast, and run artifacts remain separately evidence-bound. Never overwrite a prior terminal attempt.
