# Architecture

The system separates probabilistic research interpretation from deterministic state/data machinery.

## Owning planes

**DEFINITION / behavioral policy** — `AGENTS.md`, `.codex/agents/*.toml`, `.agents/skills/**`.

**POLICY / authority** — Codex sandbox, approval policy, MCP/app permissions, network policy, host-managed OAuth, and user authorization. Repository instructions do not grant those permissions.

**EXTERNAL ACQUISITION** — configured Massive MCP server for endpoint discovery, authenticated retrieval, pagination, transient workspace staging, and SQL/query operations.

**DURABLE DATA PLANE** — repository-owned canonical JSONL materialization, row-count/key verification, SHA-256 binding, point-in-time/cutoff enforcement, and immutable acquisition manifests.

**DETERMINISTIC RESEARCH PIPELINE** — feature store, market state, cross-sectional factor ranks, BTC/ETH/market residual model, macro coverage, ensemble, research-only risk sizing, forecast payload, and frozen forecast ledger.

**ORCHESTRATION / REVIEW** — primary Codex research-director plus named independent analytical/review roles.

## Capability model

Every external capability has three facts: discovery, dated snapshot status, and actual authenticated access. `config/daily-capabilities.json` assigns severity:

- CORE: required to produce a daily crypto forecast;
- ENRICHMENT: broadens cross-asset context; denial yields explicit DEGRADED coverage;
- EVENT_OPTIONAL: event-driven intelligence, skipped when unavailable unless an active registered design requires it.

This avoids treating provider/account entitlement mismatch as either permission to bypass or an unnecessary kill switch for otherwise valid core research.

## Daily topology

```text
stable daily run_id + fresh attempt_id
        |
local preflight / prior-run discovery
        |
Massive capability probes
(discovery + snapshot + authenticated access)
        |
capability evaluation
        |
Massive MCP staged acquisition
        |
bounded query_data export chunks
        |
deterministic immutable materialization
(row count + unique keys + SHA-256)
        |
sealed COMPLETE / DEGRADED acquisition
        |
   data-steward
        |
deterministic daily pipeline
(feature store -> state -> factors -> residual -> macro coverage -> ensemble -> risk)
        |
        +-- crypto-internals --------+
        +-- relative-value ----------+ parallel
        +-- macro-regime ------------+
        +-- institutional-intel -----+
                                      |
                              synthesis barrier
                                      |
                               portfolio-risk
                                      |
                            methodology-auditor
                                      |
                               primary adjudication
                                      |
                          immutable forecast freeze
                                      |
                          later OOS scorekeeping
```

A transient Massive workspace is never the governed data record. Agent prose is never the deterministic calculation authority.

## Two-phase crypto core

The first MCP phase fixes the PIT universe and cutoff-day cross-section. Deterministic code then selects the configured liquid USD universe. The second phase retrieves the historical lookback only for that fixed eligible set plus BTC/ETH anchors. This keeps the daily acquisition bounded while preserving a proper historical feature/residual model.

## Attempt lineage

`run_id` identifies the stable research date; every retry receives a new `attempt_id`. Prior terminal artifacts are never overwritten. Release packages intentionally ship no date-specific runtime research artifacts.

## Research topology

```text
preregister hypothesis
        |
fixed governed materialized source snapshot
        |
factor-researcher
        |
statistical-validator
        |
methodology-auditor
        |
deterministic promotion gate
        |
primary adjudication / immutable state transition
```

No agent recommendation or MCP result is itself a state transition.
