from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

AGENTS = [
    "data-steward", "crypto-internals", "relative-value", "macro-regime",
    "institutional-intelligence", "factor-researcher", "statistical-validator",
    "portfolio-risk", "methodology-auditor",
]
WORKFLOW_SKILLS = [
    "daily-research-run", "factor-research", "candidate-validation",
    "methodology-audit", "oos-scorekeeping",
]
SUPPORT_SKILLS = ["massive-basic-endpoints", "massive-mcp-data-plane"]
SKILLS = WORKFLOW_SKILLS + SUPPORT_SKILLS
SCHEMAS = [
    "hypothesis.schema.json", "agent_handoff.schema.json", "validation_report.schema.json",
    "audit_report.schema.json", "data_quality_report.schema.json", "forecast_record.schema.json",
    "outcome_record.schema.json", "promotion_decision.schema.json",
    "massive_acquisition_manifest.schema.json",
    "capability_probe_report.schema.json", "capability_evaluation.schema.json",
    "materialized_dataset.schema.json", "daily_pipeline_result.schema.json",
]
TRANSIENT_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
TRANSIENT_SUFFIXES = {".pyc", ".pyo", ".tmp", ".swp"}
MASSIVE_MCP_URL = "https://mcp.massive.com/"


def parse_skill_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening YAML frontmatter delimiter")
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration as exc:
        raise ValueError("missing closing YAML frontmatter delimiter") from exc
    meta: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"unsupported frontmatter line: {line}")
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"\'')
    return meta, "\n".join(lines[end + 1:]).strip()


def check_skill(name: str, errors: list[str]) -> None:
    skill_dir = ROOT / ".agents" / "skills" / name
    path = skill_dir / "SKILL.md"
    if not path.is_file():
        errors.append(f"missing-skill:{name}")
        return
    try:
        meta, body = parse_skill_frontmatter(path)
    except ValueError as exc:
        errors.append(f"invalid-skill-frontmatter:{name}:{exc}")
        return
    if meta.get("name") != name:
        errors.append(f"skill-name-mismatch:{name}:{meta.get('name', '')}")
    description = meta.get("description", "")
    if not description:
        errors.append(f"skill-missing-description:{name}")
    elif len(description) > 1024:
        errors.append(f"skill-description-too-long:{name}:{len(description)}")
    elif "use " not in description.lower():
        errors.append(f"skill-description-missing-activation-boundary:{name}")
    if not body:
        errors.append(f"skill-empty-body:{name}")

    for rel in re.findall(r"`(\.\./\.\./\.\./[^`]+)`", body):
        target = (skill_dir / rel).resolve()
        try:
            target.relative_to(ROOT)
        except ValueError:
            errors.append(f"skill-reference-escapes-root:{name}:{rel}")
            continue
        if not target.exists():
            errors.append(f"skill-broken-reference:{name}:{rel}")

    for nested in re.findall(r"\$([a-z0-9][a-z0-9-]*)", body):
        if nested not in SKILLS:
            errors.append(f"skill-unknown-nested-skill:{name}:{nested}")

    sidecar = skill_dir / "agents" / "openai.yaml"
    if not sidecar.is_file():
        errors.append(f"skill-missing-openai-yaml:{name}")
        return
    text = sidecar.read_text(encoding="utf-8")
    for field in ("display_name:", "short_description:", "default_prompt:"):
        if field not in text:
            errors.append(f"skill-openai-yaml-missing:{name}:{field[:-1]}")
    match = re.search(r'^\s*short_description:\s*"([^"]*)"\s*$', text, re.MULTILINE)
    if match and not 25 <= len(match.group(1)) <= 64:
        errors.append(f"skill-short-description-length:{name}:{len(match.group(1))}")
    if f"${name}" not in text:
        errors.append(f"skill-default-prompt-missing-explicit-name:{name}")

    if name == "massive-mcp-data-plane":
        required_fragments = [
            'type: "mcp"', 'value: "massive"',
            'transport: "streamable_http"', f'url: "{MASSIVE_MCP_URL}"',
        ]
        for fragment in required_fragments:
            if fragment not in text:
                errors.append(f"massive-mcp-skill-dependency-missing:{fragment}")


def check_agent(name: str, errors: list[str]) -> None:
    path = ROOT / ".codex" / "agents" / f"{name}.toml"
    if not path.is_file():
        errors.append(f"missing-agent:{name}")
        return
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        errors.append(f"invalid-agent-toml:{name}:{exc}")
        return
    for field in ("name", "description", "developer_instructions"):
        if not data.get(field):
            errors.append(f"agent-missing:{name}:{field}")
    if data.get("name") != name:
        errors.append(f"agent-name-mismatch:{name}:{data.get('name', '')}")
    if "sandbox_mode" in data:
        errors.append(f"agent-role-sandbox-mode-not-enforced:{name}")


def check_python_network_bypass(errors: list[str]) -> None:
    forbidden = {
        "import requests": "requests",
        "from requests": "requests",
        "import httpx": "httpx",
        "from httpx": "httpx",
        "import urllib.request": "urllib.request",
        "MASSIVE_API_KEY": "MASSIVE_API_KEY",
        "POLYGON_API_KEY": "POLYGON_API_KEY",
    }
    validator_path = Path(__file__).resolve()
    for path in ROOT.rglob("*.py"):
        if path.resolve() == validator_path:
            continue
        text = path.read_text(encoding="utf-8")
        for needle, label in forbidden.items():
            if needle in text:
                errors.append(f"direct-network-bypass:{path.relative_to(ROOT).as_posix()}:{label}")


def check_package_hygiene(errors: list[str]) -> None:
    for path in ROOT.rglob("*"):
        rel = path.relative_to(ROOT)
        if any(part in TRANSIENT_PARTS for part in rel.parts):
            errors.append(f"transient-path:{rel.as_posix()}")
        elif path.is_file() and path.suffix.lower() in TRANSIENT_SUFFIXES:
            errors.append(f"transient-file:{rel.as_posix()}")



def check_daily_config(errors: list[str]) -> None:
    try:
        matrix = json.loads((ROOT / "config" / "daily-capabilities.json").read_text(encoding="utf-8"))
        capabilities = matrix.get("capabilities", [])
        ids = [item.get("capability_id") for item in capabilities if isinstance(item, dict)]
        if len(ids) != len(set(ids)):
            errors.append("daily-capabilities:duplicate-capability-id")
        requirements = {item.get("requirement") for item in capabilities if isinstance(item, dict)}
        if not {"CORE", "ENRICHMENT", "EVENT_OPTIONAL"}.issubset(requirements):
            errors.append(f"daily-capabilities:missing-requirement-class:{sorted(requirements)}")
        required_core = {"crypto_universe_pit", "crypto_grouped_eod", "crypto_history"}
        core_ids = {item.get("capability_id") for item in capabilities if isinstance(item, dict) and item.get("requirement") == "CORE"}
        if not required_core.issubset(core_ids):
            errors.append(f"daily-capabilities:missing-core:{sorted(required_core-core_ids)}")
    except Exception as exc:
        errors.append(f"daily-capabilities:invalid:{exc}")
    try:
        model = json.loads((ROOT / "config" / "daily-model.json").read_text(encoding="utf-8"))
        weights = model.get("factor_weights", {})
        if abs(sum(float(value) for value in weights.values()) - 1.0) > 1e-9:
            errors.append("daily-model:factor-weights-must-sum-to-1")
        if int(model.get("minimum_history_observations", 0)) < 30:
            errors.append("daily-model:minimum-history-too-small")
        if int(model.get("eligible_top_n", 0)) < 5:
            errors.append("daily-model:eligible-top-n-too-small")
    except Exception as exc:
        errors.append(f"daily-model:invalid:{exc}")


def check_release_state_clean(errors: list[str]) -> None:
    governed = ["research/acquisitions", "research/runs", "research/forecasts", "research/data", "research/pipeline"]
    for rel in governed:
        root = ROOT / rel
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.name != ".gitkeep":
                errors.append(f"release-seeded-runtime-artifact:{path.relative_to(ROOT).as_posix()}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", action="store_true", help="also fail on transient packaging artifacts")
    args = ap.parse_args()

    errors: list[str] = []
    required = [
        "AGENTS.md", ".codex/config.toml", "workflows/daily-goal.md", "workflows/research-goal.md",
        "docs/data-capability-boundary.md", "docs/massive-mcp-data-plane.md",
        "docs/research-state-model.md", "contracts/agent-handoff.md",
        "scripts/control_plane/seal_acquisition.py",
        "scripts/control_plane/preflight.py", "scripts/control_plane/discover_run.py",
        "scripts/control_plane/evaluate_capabilities.py", "scripts/control_plane/materialize_mcp_dataset.py",
        "scripts/control_plane/validate_artifact.py", "scripts/control_plane/run_python.ps1", "scripts/pipeline/run_daily_pipeline.py",
        ".agents/skills/massive-basic-endpoints/scripts/endpoint_lookup.ps1",
        "config/daily-capabilities.json", "config/daily-model.json",
    ]
    for rel in required:
        if not (ROOT / rel).is_file():
            errors.append(f"missing:{rel}")

    try:
        config = tomllib.loads((ROOT / ".codex" / "config.toml").read_text(encoding="utf-8"))
        agent_cfg = config.get("agents", {})
        if "job_max_runtime_seconds" in agent_cfg:
            errors.append("obsolete-agent-config:job_max_runtime_seconds")
        if "max_threads" in agent_cfg:
            errors.append("legacy-agent-config:max_threads")
        if agent_cfg.get("max_depth") != 1:
            errors.append(f"agent-config-max-depth:{agent_cfg.get('max_depth', 'MISSING')}")
        massive_cfg = config.get("mcp_servers", {}).get("massive", {})
        if massive_cfg.get("url") != MASSIVE_MCP_URL:
            errors.append(f"massive-mcp-config-url:{massive_cfg.get('url', 'MISSING')}")
    except (OSError, tomllib.TOMLDecodeError) as exc:
        errors.append(f"invalid-config-toml:{exc}")

    agents_text = (ROOT / "AGENTS.md").read_text(encoding="utf-8") if (ROOT / "AGENTS.md").is_file() else ""
    for phrase in ("Massive MCP", "$massive-mcp-data-plane", "Do not bypass"):
        if phrase not in agents_text:
            errors.append(f"agents-missing-massive-policy:{phrase}")

    for name in AGENTS:
        check_agent(name, errors)
    for name in SKILLS:
        check_skill(name, errors)
    for name in SCHEMAS:
        path = ROOT / "schemas" / name
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"invalid-schema-json:{name}:{exc}")

    check_daily_config(errors)
    check_python_network_bypass(errors)
    if args.package:
        check_package_hygiene(errors)
        check_release_state_clean(errors)

    if errors:
        print("\n".join(sorted(set(errors))))
        return 1
    print(
        f"PASS: {len(AGENTS)} agents, {len(SKILLS)} skills "
        f"({len(WORKFLOW_SKILLS)} workflow + {len(SUPPORT_SKILLS)} support), "
        f"{len(SCHEMAS)} schemas, Massive MCP configured, deterministic daily pipeline present"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
