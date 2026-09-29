# Research state model

## Candidate lifecycle

```text
REGISTERED
  -> RESEARCHED
  -> VALIDATED
  -> AUDITED
  -> PROMOTED | REJECTED | INCONCLUSIVE | INVALID
```

Only deterministic code may write promotion state.

## Required evidence before promotion

A candidate may be promoted only if all are true:

1. hypothesis was preregistered and its multiple-testing family is declared;
2. data-quality status is `PASS`;
3. independent `statistical-validator` verdict is `PROMOTE`;
4. validation checks pass for chronology, leakage, multiple testing, uncertainty, parameter stability, regime dependence, turnover, cost scenarios, and OOS evidence;
5. `methodology-auditor` status is `PASS` for the same candidate and hypothesis;
6. validation and audit evidence arrays are non-empty and identities agree;
7. promotion has not already been recorded.

The gate does not authorize trading, network access, or external writes. It only controls this repository's research-state transition.

## Audit subjects

Methodology audits are explicit about subject identity:

- candidate audits use `subject_type = candidate` and bind `subject_id`, `candidate_id`, and `hypothesis_id`;
- daily-run audits use `subject_type = daily_run` and bind `subject_id` plus `run_id`.

A missing or ambiguous subject identity cannot satisfy a candidate promotion gate.

## Forecast lifecycle

A forecast is created before its target outcome exists and written immutably to `research/forecasts/`. Rewriting the same forecast ID is forbidden. Stored forecasts carry a content digest; the research cutoff may not occur after forecast creation.

Once the target horizon matures, scorekeeping writes a separate outcome artifact under `research/outcomes/` that binds to the forecast ID and digest. Never rewrite the original forecast with realized results. If the repository has no authoritative deterministic scorer for the registered metric, scorekeeping is inconclusive rather than model-invented.
