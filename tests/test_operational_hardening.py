import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "scripts" / "control_plane"
PIPELINE = ROOT / "scripts" / "pipeline"


def run(path, *args, cwd=ROOT):
    return subprocess.run([sys.executable, str(path), *map(str, args)], cwd=cwd, text=True, capture_output=True)


def write_materialized(root: Path, attempt: str, dataset_id: str, rows: list[dict], market="Crypto") -> Path:
    out = root / attempt
    out.mkdir(parents=True, exist_ok=True)
    data = out / f"{dataset_id}.jsonl"
    body = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows)
    data.write_text(body, encoding="utf-8")
    digest = "sha256:" + hashlib.sha256(body.encode()).hexdigest()
    meta = {
        "dataset_id": dataset_id,
        "run_id": "2026-09-28-eod",
        "attempt_id": attempt,
        "market": market,
        "endpoint_path": "/test",
        "params": {},
        "requirement": "CORE",
        "research_cutoff": "2026-09-28T23:59:59Z",
        "retrieved_at": "2026-09-29T00:00:01Z",
        "as_of": "2026-09-28",
        "row_count": len(rows),
        "sort_fields": [],
        "key_fields": [],
        "data_path": data.as_posix(),
        "data_digest": digest,
        "source_chunks": [],
        "materialization_status": "VERIFIED",
    }
    (out / f"{dataset_id}.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return data


class OperationalHardeningTests(unittest.TestCase):
    def test_capability_evaluation_degrades_for_stock_index_denial(self):
        matrix = json.loads((ROOT / "config" / "daily-capabilities.json").read_text(encoding="utf-8"))
        caps = []
        for item in matrix["capabilities"]:
            access = "SUCCEEDED"
            if item["capability_id"] in {"stock_macro_proxies", "index_macro_proxies"}:
                access = "NOT_ENTITLED"
            caps.append({
                "capability_id": item["capability_id"],
                "discovery_status": "VERIFIED",
                "basic_snapshot_status": "INCLUDED",
                "access_status": access,
                "endpoint_path": "/test",
                "probe_params": {},
                "probed_at": "2026-09-29T00:00:00Z",
                "evidence": ["test"],
            })
        report = {
            "run_id": "2026-09-28-eod",
            "attempt_id": "a1",
            "created_at": "2026-09-29T00:00:00Z",
            "research_cutoff": "2026-09-28T23:59:59Z",
            "capabilities": caps,
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "probe.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            proc = run(CONTROL / "evaluate_capabilities.py", path)
            self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
            result = json.loads(proc.stdout)
            self.assertEqual("DEGRADED", result["status"])
            self.assertFalse(result["core_failures"])
            self.assertEqual(2, len(result["degradations"]))

    def test_capability_evaluation_blocks_for_core_denial(self):
        matrix = json.loads((ROOT / "config" / "daily-capabilities.json").read_text(encoding="utf-8"))
        caps = []
        for item in matrix["capabilities"]:
            caps.append({
                "capability_id": item["capability_id"],
                "discovery_status": "VERIFIED",
                "basic_snapshot_status": "INCLUDED",
                "access_status": "NOT_ENTITLED" if item["capability_id"] == "crypto_history" else "SUCCEEDED",
                "endpoint_path": "/test",
                "probe_params": {},
                "probed_at": "2026-09-29T00:00:00Z",
                "evidence": ["test"],
            })
        report = {"run_id": "r", "attempt_id": "a", "created_at": "2026-09-29T00:00:00Z", "research_cutoff": "2026-09-28T23:59:59Z", "capabilities": caps}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "probe.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            proc = run(CONTROL / "evaluate_capabilities.py", path)
            self.assertEqual(2, proc.returncode)
            self.assertEqual("BLOCKED", json.loads(proc.stdout)["status"])

    def test_materializer_verifies_count_digest_and_immutability(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            c1 = td / "one.csv"
            c2 = td / "two.csv"
            c1.write_text("ticker,t,c\nX:BTCUSD,1,10\n", encoding="utf-8")
            c2.write_text("ticker,t,c\nX:ETHUSD,1,20\n", encoding="utf-8")
            out = td / "data"
            args = [c1, c2, "--dataset-id", "crypto", "--run-id", "r", "--attempt-id", "a", "--market", "Crypto", "--endpoint-path", "/test", "--params-json", "{}", "--requirement", "CORE", "--research-cutoff", "2026-09-28T23:59:59Z", "--retrieved-at", "2026-09-29T00:00:01Z", "--as-of", "2026-09-28", "--expected-rows", "2", "--sort-fields", "ticker,t", "--key-fields", "ticker,t", "--out-dir", out]
            first = run(CONTROL / "materialize_mcp_dataset.py", *args)
            self.assertEqual(0, first.returncode, first.stdout + first.stderr)
            result = json.loads(first.stdout)
            self.assertEqual(2, result["row_count"])
            meta = Path(result["metadata"])
            self.assertTrue(meta.exists())
            second = run(CONTROL / "materialize_mcp_dataset.py", *args)
            self.assertEqual(3, second.returncode)

    def test_materializer_rejects_truncated_chunk(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            chunk = td / "bad.csv"
            chunk.write_text("ticker,t,c\nX:BTCUSD,1,[truncated: 9 more chars]\n", encoding="utf-8")
            proc = run(CONTROL / "materialize_mcp_dataset.py", chunk, "--dataset-id", "crypto", "--run-id", "r", "--attempt-id", "a", "--market", "Crypto", "--endpoint-path", "/test", "--params-json", "{}", "--requirement", "CORE", "--research-cutoff", "2026-09-28T23:59:59Z", "--retrieved-at", "2026-09-29T00:00:01Z", "--as-of", "2026-09-28", "--expected-rows", "1", "--out-dir", td / "out")
            self.assertEqual(2, proc.returncode)
            self.assertIn("truncation_marker", proc.stdout)

    def test_degraded_acquisition_allows_denied_enrichment_but_complete_core(self):
        payload = json.loads((ROOT / "examples" / "acquisition.example.json").read_text(encoding="utf-8"))
        payload["status"] = "DEGRADED"
        payload["limitations"] = ["stock_macro_proxies:not_entitled"]
        payload["datasets"].append({
            "dataset_id": "stock_macro",
            "capability_id": "stock_macro_proxies",
            "requirement": "ENRICHMENT",
            "market": "Stocks",
            "purpose": "macro",
            "method": "GET",
            "endpoint_path": "/v2/aggs/grouped/locale/us/market/stocks/2026-09-28",
            "params": {},
            "retrieved_at": "2026-09-29T00:03:00Z",
            "retrieval_time_source": "CLIENT_CAPTURED",
            "as_of": "2026-09-28",
            "discovery_status": "VERIFIED",
            "basic_snapshot_status": "INCLUDED",
            "access_status": "NOT_ENTITLED",
            "pagination_complete": True,
            "row_count": 0,
            "workspace_table": None,
            "request_ids": [],
            "materialization_status": "NOT_REQUIRED",
            "materialized_path": None,
            "materialized_digest": None,
            "materialized_row_count": None,
            "status": "ACCESS_DENIED",
            "notes": ["provider denial"],
        })
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            src = td / "payload.json"
            src.write_text(json.dumps(payload), encoding="utf-8")
            proc = run(CONTROL / "seal_acquisition.py", src, "--out-dir", td / "out")
            self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)

    def test_validate_artifact_enforces_additional_properties(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            artifact = json.loads((ROOT / "examples" / "data-quality.example.json").read_text(encoding="utf-8"))
            artifact["unexpected"] = True
            src = td / "dq.json"
            src.write_text(json.dumps(artifact), encoding="utf-8")
            proc = run(CONTROL / "validate_artifact.py", src, ROOT / "schemas" / "data_quality_report.schema.json")
            self.assertEqual(1, proc.returncode)
            self.assertIn("additionalProperty:unexpected", proc.stdout)

    def test_deterministic_pipeline_runs_with_verified_crypto_core_and_degraded_macro(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            attempt = "2026-09-28-eod-attempt-test"
            tickers = ["X:BTCUSD", "X:ETHUSD", "X:SOLUSD", "X:XRPUSD", "X:LTCUSD", "X:ADAUSD"]
            universe = [{"ticker": t, "active": True} for t in tickers]
            cutoff = []
            history = []
            start = datetime(2026, 7, 26, tzinfo=timezone.utc)
            for j, ticker in enumerate(tickers):
                base = 100 + j * 20
                for i in range(65):
                    price = base * (1 + 0.002 * (j + 1) * i)
                    ts = int((start + timedelta(days=i)).timestamp() * 1000)
                    history.append({"ticker": ticker, "t": ts, "o": price * 0.997, "h": price * 1.01, "l": price * 0.99, "c": price, "v": 100000 + 1000 * j, "vw": price * 0.999, "n": 1000 + i})
                last = history[-1]
                cutoff.append({"T": ticker, "t_2": last["t"], "o": last["o"], "h": last["h"], "l": last["l"], "c": last["c"], "v": last["v"], "vw": last["vw"], "n": last["n"]})
            data_root = td / "data"
            p_universe = write_materialized(data_root, attempt, "crypto_universe", universe)
            p_cutoff = write_materialized(data_root, attempt, "crypto_grouped_cutoff", cutoff)
            p_history = write_materialized(data_root, attempt, "crypto_history", history)
            dq = td / "dq.json"
            dq.write_text(json.dumps({"run_id": "2026-09-28-eod", "status": "PASS", "cutoff": "2026-09-28T23:59:59Z", "datasets": ["crypto_universe", "crypto_grouped_cutoff", "crypto_history"], "findings": []}), encoding="utf-8")
            caps = td / "caps.json"
            caps.write_text(json.dumps({"run_id": "2026-09-28-eod", "attempt_id": attempt, "status": "DEGRADED", "core_failures": [], "degradations": ["stock_macro_proxies:NOT_ENTITLED", "index_macro_proxies:NOT_ENTITLED"], "optional_unavailable": [], "evaluated_capabilities": []}), encoding="utf-8")
            out = td / "pipeline"
            proc = run(PIPELINE / "run_daily_pipeline.py", "--run-id", "2026-09-28-eod", "--attempt-id", attempt, "--research-cutoff", "2026-09-28T23:59:59Z", "--crypto-universe", p_universe, "--crypto-cutoff", p_cutoff, "--crypto-history", p_history, "--data-quality", dq, "--capability-evaluation", caps, "--config", ROOT / "config" / "daily-model.json", "--out-dir", out)
            self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
            result = json.loads((out / attempt / "pipeline-result.json").read_text(encoding="utf-8"))
            self.assertEqual("DEGRADED", result["status"])
            self.assertEqual(6, result["history_qualified_assets"])
            self.assertIn(result["market_state"], {"RISK_ON", "TRANSITION", "RISK_OFF"})
            self.assertTrue((out / attempt / "forecast-payload.json").exists())


if __name__ == "__main__":
    unittest.main()
