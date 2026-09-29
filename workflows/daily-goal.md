# Daily `/goal`

Use one stable daily `run_id` and a fresh `attempt_id` for every retry.

```text
/goal Execute one complete governed end-of-day crypto research attempt for <DATE> through the strongest valid terminal state.

Use the repository control plane exactly. Do not stop after planning.

0. PREFLIGHT / ATTEMPT IDENTITY
- Stable run_id: <DATE>-eod.
- Create a unique attempt_id; never overwrite a prior attempt.
- Run scripts/control_plane/preflight.py and discover_run.py before acquiring data.
- If required deterministic scripts cannot execute, BLOCK before spending MCP calls. Git unavailability is a reported verification limitation, not by itself a research blocker.

1. EFFECTIVE MASSIVE CAPABILITY PROBE
- Read config/daily-capabilities.json.
- Through Massive MCP, independently record endpoint discovery, dated Basic snapshot status, and actual authenticated access for each applicable capability.
- Write an attempt-scoped capability probe report and run evaluate_capabilities.py.
- CORE failure => BLOCKED.
- ENRICHMENT failure => DEGRADED coverage, not automatic BLOCK.
- EVENT_OPTIONAL unavailable => record unavailable/skip unless this run explicitly requires it.
- Never bypass Massive MCP.

2. FIX AND DURABLY MATERIALIZE THE SOURCE SET
- Acquire point-in-time crypto universe and cutoff-day grouped crypto cross-section first.
- Materialize both with scripts/control_plane/materialize_mcp_dataset.py; transient MCP workspace tables do not count as durable evidence.
- From that fixed cross-section, deterministically select the configured top-N eligible USD pairs and anchors according to config/daily-model.json.
- Acquire the configured historical lookback for that fixed selected universe through Massive MCP, using bounded calls and complete pagination.
- For workspace tables, export ordered 100-200 row query_data chunks; materialize canonical JSONL; verify exact staged/local row counts, unique keys, and SHA-256 digests.
- Acquire/materialize accessible ENRICHMENT inputs (FX, stock, index) and relevant EVENT_OPTIONAL inputs without broadening the run after downstream results are seen.
- Capture exact client UTC timestamps around MCP calls when server timestamps/request IDs are unavailable; do not estimate them.
- Seal the acquisition only after durable materialization. PARTIAL is not downstream-eligible. DEGRADED is downstream-eligible only when every CORE dataset is COMPLETE and verified.

3. DATA-STEWARD GATE
- Delegate data-steward against the sealed acquisition, capability evaluation, and materialized metadata/data.
- CORE missing/denied/transient/incomplete/post-cutoff => BLOCK.
- Missing ENRICHMENT => normally DEGRADED if core remains valid.
- Validate the handoff against schemas/agent_handoff.schema.json and the data-quality artifact against schemas/data_quality_report.schema.json with validate_artifact.py.

4. DETERMINISTIC PIPELINE
- If data quality permits continuation, run scripts/pipeline/run_daily_pipeline.py over the verified materialized data.
- Code owns feature calculations, rankings, residual model, market state, ensemble, research-only risk sizing, persistence, and forecast payload creation.
- Validate pipeline-result.json against schemas/daily_pipeline_result.schema.json.
- If the deterministic pipeline cannot execute or history coverage is insufficient, BLOCK rather than substituting prose calculations.

5. PARALLEL ANALYSIS
Run crypto-internals, relative-value, macro-regime, and institutional-intelligence in parallel over the fixed deterministic artifacts.
- Missing macro ENRICHMENT must be reported as DEGRADED/UNAVAILABLE coverage, never invented or silently neutralized.
- Institutional source unavailability is distinct from no material event.
- No agent may independently refresh the fixed run dataset.
- Validate every handoff artifact against agent_handoff.schema.json.

6. SYNTHESIS -> PORTFOLIO-RISK -> METHODOLOGY AUDIT
- Primary Codex reconciles deterministic outputs and the four handoffs.
- Run portfolio-risk on the deterministic research-only proposal.
- Run methodology-auditor fresh. A denied ENRICHMENT is acceptable only when explicitly degraded and no claim depends on it. CORE failure, direct-network workaround, transient-only core data, or cutoff leakage is blocking.
- Validate audit artifact against audit_report.schema.json.

7. FREEZE FORECAST
- If mandatory gates permit it, freeze the deterministic forecast payload with freeze_forecast.py before its target outcome exists.
- Verify immutable rewrite rejection.
- A DEGRADED forecast is permitted only when CORE is complete, the data-steward permits continuation, the deterministic pipeline completes, and methodology audit passes while preserving the degradation in source evidence.

8. VERIFY
- Validate every produced JSON artifact against its declared schema using validate_artifact.py.
- Run validate_control_plane.py, relevant tests, and Git checks when a Git checkout is actually available.
- Report exact commands and outcomes, not inferred success.

Final report: status; run_id/attempt_id; cutoff; effective capability matrix; acquisition/materialization digests; data-quality result; deterministic pipeline result; four analytical handoffs; portfolio-risk result; methodology audit; frozen forecast path/digest if any; executed verification; files created; unresolved limitations.
```
