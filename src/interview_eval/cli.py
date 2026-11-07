from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .io import write_json
from .runner import compare_reports, run_evaluation


def _load_object(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(prog="interview-eval",
        description="Run deterministic offline evaluations for interview agents.")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="evaluate a JSONL dataset")
    run.add_argument("--dataset", required=True)
    run.add_argument("--thresholds", default="configs/thresholds.json")
    run.add_argument("--output", default="reports/latest.json")
    compare = commands.add_parser("compare", help="compare baseline and candidate dimension means")
    compare.add_argument("--baseline", required=True)
    compare.add_argument("--candidate", required=True)
    compare.add_argument("--max-delta", type=float, default=1.0)
    compare.add_argument("--output", default="reports/comparison.json")
    args = parser.parse_args()
    try:
        if args.command == "run":
            thresholds = _load_object(args.thresholds) if Path(args.thresholds).exists() else {}
            report = run_evaluation(args.dataset, thresholds)
        else:
            report = compare_reports(_load_object(args.baseline), _load_object(args.candidate),
                                     args.max_delta)
        write_json(args.output, report)
        print(json.dumps(report, indent=2))
        if not report.get("summary", {}).get("passed", report.get("passed", False)):
            sys.exit(1)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
