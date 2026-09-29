# Massive MCP data plane

Massive MCP is the authoritative external source plane. Repository code owns durable materialization, normalization, calculation, sealing, and state transitions.

## Operational sequence

### 0. Local preflight before acquisition

Before spending MCP calls, create a stable `run_id` (for example `2026-09-28-eod`) and a unique immutable `attempt_id` (for example `2026-09-28-eod-attempt-20260929T020000Z`). Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE="1"
python .\scripts\control_plane\preflight.py `
  --run-id 2026-09-28-eod `
  --attempt-id 2026-09-28-eod-attempt-20260929T020000Z `
  --research-cutoff 2026-09-28T23:59:59Z
python .\scripts\control_plane\discover_run.py 2026-09-28-eod
```

Preflight checks the local deterministic stage surface and writable artifact directories. Git availability is informative, not a market-data gate. Never overwrite a prior terminal attempt.

### 1. Probe effective access before large acquisition

For every capability in `config/daily-capabilities.json`, record three independent facts:

1. `discovery_status`: can Massive MCP describe the endpoint now?
2. `basic_snapshot_status`: did the dated Basic snapshot mark the capability included?
3. `access_status`: did a bounded authenticated MCP call actually succeed?

Write an attempt-scoped capability probe report and evaluate it with:

```powershell
python .\scripts\control_plane\evaluate_capabilities.py `
  research\runs\<attempt>.capability-probes.json `
  --out research\runs\<attempt>.capability-evaluation.json
```

Severity is explicit:

- `CORE`: unresolved/denied access blocks.
- `ENRICHMENT`: denial degrades coverage but does not kill a valid crypto-core run.
- `EVENT_OPTIONAL`: denial/absence is recorded and skipped unless a registered design explicitly requires it.

A provider denial always wins over a static entitlement snapshot. Never bypass it.

### 2. Two-phase core acquisition

The daily model uses a bounded two-phase crypto acquisition:

1. materialize the point-in-time universe and cutoff-day grouped crypto cross-section;
2. deterministically select the configured liquid USD universe from that fixed cross-section, then acquire the configured historical lookback for those selected assets plus BTC/ETH.

This avoids both a 120-day full-market grouped crawl and a survivorship-biased current-ticker backtest.

Current defaults are in `config/daily-model.json`: top 25 liquid USD pairs, 120 calendar days requested, and at least 60 observations required for deterministic features.

### 3. Durable MCP materialization protocol

`call_api(..., store_as=...)` and a Massive workspace are staging only. They are never sufficient evidence by themselves.

For every staged table:

1. use `query_data(action="describe")` or `show_tables` to record schema and exact staged row count;
2. choose stable ordering/key fields (`ticker,timestamp`, or the closest endpoint-specific equivalent);
3. export bounded ordered slices with `query_data`, normally 100-200 rows per call;
4. capture each slice exactly as CSV, JSON, or JSONL under an attempt-scoped staging directory;
5. run `scripts/control_plane/materialize_mcp_dataset.py` over all chunks with the expected row count, stable sort fields, and unique key fields;
6. reject truncation markers, malformed chunks, duplicate keys, and row-count mismatches;
7. persist canonical immutable JSONL plus a sidecar metadata file containing the local SHA-256 digest.

Example:

```powershell
python .\scripts\control_plane\materialize_mcp_dataset.py `
  research\staging\<attempt>\crypto-cutoff\chunk-*.csv `
  --dataset-id crypto_grouped_cutoff `
  --run-id 2026-09-28-eod `
  --attempt-id <attempt> `
  --market Crypto `
  --endpoint-path /v2/aggs/grouped/locale/global/market/crypto/2026-09-28 `
  --params-json '{"adjusted":true}' `
  --requirement CORE `
  --research-cutoff 2026-09-28T23:59:59Z `
  --retrieved-at <exact-client-captured-UTC-time> `
  --as-of 2026-09-28 `
  --expected-rows <workspace-row-count> `
  --sort-fields T,t_2 `
  --key-fields T,t_2
```

For custom-bar history fetched one ticker at a time, make each `query_data` slice add the literal ticker as a `ticker` column and combine all slices into one `crypto_history` materialization. The deterministic pipeline expects `ticker` plus OHLC/VWAP/volume/timestamp fields.

### 4. Provenance timing

If MCP does not expose server request IDs/timestamps, capture a real client-side UTC timestamp immediately around each call. Record `retrieval_time_source=CLIENT_CAPTURED`. Do not manually estimate a minute-level time and label it exact. Missing provider request IDs are a limitation, not permission to invent them.

### 5. Seal only after durable evidence exists

The acquisition manifest may be:

- `COMPLETE`: all core and attempted required enrichments are verified/materialized;
- `DEGRADED`: every core dataset is verified/materialized, but one or more enrichment families are unavailable/incomplete and explicitly recorded;
- `PARTIAL`: in-progress/incomplete; not eligible for downstream analysis;
- `BLOCKED`: a core requirement failed.

For `COMPLETE` or `DEGRADED`, every `CORE` dataset must have successful authenticated access, complete pagination, non-approximate retrieval time, exact local row-count agreement, immutable materialization path, and SHA-256 digest.

### 6. Deterministic daily pipeline

After the independent data-steward returns PASS or an explicitly acceptable DEGRADED result, run `scripts/pipeline/run_daily_pipeline.py`. It consumes only verified materialized datasets and produces inspectable feature-store, market-state, factor, residual/relative-value, macro-coverage, ensemble, risk, and forecast-payload artifacts.

The pipeline refuses a BLOCK data-quality result, a BLOCKED capability evaluation, digest/row-count mismatches, insufficient history coverage, or missing BTC/ETH anchors.

## No-bypass rule

Do not use direct REST/HTTP clients, curl, requests/httpx, Massive/Polygon SDKs, copied API keys, web search, or alternate providers as substitutes for a denied Massive capability. Degrade or block according to the declared capability class.
