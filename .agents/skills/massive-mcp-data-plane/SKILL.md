---
name: massive-mcp-data-plane
description: Acquire and stage Massive-backed research data through the configured Massive MCP server with Basic-plan entitlement checks, current endpoint verification, pagination, workspace reuse, cutoff discipline, and a sealed acquisition manifest. Use inside governed daily, factor-research, or OOS workflows; do not bypass Massive MCP with direct HTTP/API clients.
---

# Massive MCP data plane

Use this support skill whenever a governed workflow needs Massive source data. Read `../../../docs/massive-mcp-data-plane.md` and `../../../docs/data-capability-boundary.md` before acquisition.

## Required sequence

1. Run the local preflight before market acquisition. Confirm the deterministic pipeline/materializer/validators exist and can execute. Create a unique attempt ID; never overwrite a previous attempt.
2. Read `../../../config/daily-capabilities.json`. For every applicable capability, keep endpoint discovery, dated Basic-snapshot status, and actual authenticated access as separate evidence. Use bounded authenticated probes before large acquisitions.
3. Apply severity exactly: CORE denial/unresolved access blocks; ENRICHMENT denial degrades; EVENT_OPTIONAL denial/absence is recorded without blocking unless the active registered design explicitly requires it.
4. Use Massive MCP `search_endpoints` for current route/parameter verification and `call_api` for actual retrieval. Do not treat endpoint discovery as entitlement proof. Follow pagination completely.
5. Prefer one Massive workspace for staging. Staged tables are transient and **must not** be treated as durable run evidence.
6. Materialize every used dataset with `../../../scripts/control_plane/materialize_mcp_dataset.py`: inspect staged row count/schema, export stable ordered 100-200 row `query_data` slices, reject truncation, verify unique keys and exact local/staged row-count agreement, and persist canonical immutable JSONL + SHA-256 sidecar metadata.
7. For custom-bar history fetched per ticker, make the deterministic `query_data` projection add the literal ticker as a `ticker` column before combining chunks.
8. Capture a real UTC client timestamp immediately around each MCP call when server timestamps/request IDs are not exposed. Mark `retrieval_time_source=CLIENT_CAPTURED`; never invent request IDs or estimated exact times.
9. Check all as-of timestamps against the research cutoff. Post-cutoff data may verify schema/provenance but cannot enter the fixed run.
10. Seal the acquisition only after materialization. COMPLETE/DEGRADED require every CORE dataset to have successful authenticated access, complete pagination, verified local materialization, matching row count, and digest. PARTIAL is in-progress and not downstream-eligible.

## Completion boundary

The source plane is complete when the capability evaluation exists, every CORE dataset is durably materialized and verified, the acquisition is sealed COMPLETE or DEGRADED, and any missing enrichment is explicit. Never bypass Massive MCP with direct HTTP/API clients, SDKs, copied API keys, web search, or another provider.
