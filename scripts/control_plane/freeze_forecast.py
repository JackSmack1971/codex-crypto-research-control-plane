from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True

from common import digest, load_json, parse_timestamp, require_fields, write_new_json

REQUIRED = [
    "forecast_id", "run_id", "created_at", "research_cutoff", "target_horizon",
    "universe", "predictions", "source_artifacts"
]


def validate_forecast(obj: dict) -> list[str]:
    errors = require_fields(obj, REQUIRED, "forecast")
    if not isinstance(obj.get("predictions"), list) or not obj.get("predictions"):
        errors.append("forecast.predictions_must_be_nonempty_list")
    if not isinstance(obj.get("source_artifacts"), list) or not obj.get("source_artifacts"):
        errors.append("forecast.source_artifacts_must_be_nonempty_list")
    try:
        created_at = parse_timestamp(obj.get("created_at", ""), "forecast.created_at")
        cutoff = parse_timestamp(obj.get("research_cutoff", ""), "forecast.research_cutoff")
        if cutoff > created_at:
            errors.append("forecast.research_cutoff_after_created_at")
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("payload")
    ap.add_argument("--out-dir", default="research/forecasts")
    args = ap.parse_args()

    obj = load_json(args.payload)
    errors = validate_forecast(obj)
    if errors:
        print("\n".join(errors))
        return 2

    obj["content_digest"] = digest(obj)
    out = Path(args.out_dir) / f"{obj['forecast_id']}.json"
    try:
        write_new_json(out, obj)
    except FileExistsError:
        print(f"IMMUTABLE_CONFLICT:{out}")
        return 3
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
