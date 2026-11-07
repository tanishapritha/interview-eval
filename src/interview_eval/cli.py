from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from .benchmark import run_benchmark
from .io import write_json
from .runner import compare_reports, run_evaluation
from .shala import load_shala_export, write_case


def _load_object(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="interview-eval",
        description="Run offline checks and repeatable LLM benchmarks for interview agents.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="evaluate a JSONL dataset offline")
    run.add_argument("--dataset", required=True)
    run.add_argument("--thresholds", default="configs/thresholds.json")
    run.add_argument("--output", default="reports/latest.json")
    compare = commands.add_parser("compare", help="compare baseline and candidate dimension means")
    compare.add_argument("--baseline", required=True)
    compare.add_argument("--candidate", required=True)
    compare.add_argument("--max-delta", type=float, default=1.0)
    compare.add_argument("--output", default="reports/comparison.json")
    importer = commands.add_parser("import-shala", help="convert an Interview Shala export to JSONL")
    importer.add_argument("--input", required=True)
    importer.add_argument("--output", required=True)
    benchmark = commands.add_parser("benchmark", help="repeat the OpenRouter scorer on Shala exports")
    benchmark.add_argument("--dataset", required=True)
    benchmark.add_argument("--model", default=None)
    benchmark.add_argument("--runs", type=int, default=3)
    benchmark.add_argument("--temperature", type=float, default=0.1)
    benchmark.add_argument("--output", default="reports/benchmark.json")
    args = parser.parse_args()
    try:
        if args.command == "run":
            thresholds = _load_object(args.thresholds) if Path(args.thresholds).exists() else {}
            report = run_evaluation(args.dataset, thresholds)
            write_json(args.output, report)
            print(json.dumps(report, indent=2))
            if not report["summary"]["passed"]:
                sys.exit(1)
        elif args.command == "compare":
            report = compare_reports(_load_object(args.baseline), _load_object(args.candidate),
                                     args.max_delta)
            write_json(args.output, report)
            print(json.dumps(report, indent=2))
            if not report["passed"]:
                sys.exit(1)
        elif args.command == "import-shala":
            write_case(load_shala_export(args.input), args.output)
            print(f"Imported one Interview Shala session into {args.output}")
        else:
            from .io import load_jsonl
            report = asyncio.run(run_benchmark(
                load_jsonl(args.dataset), model=args.model, repetitions=args.runs,
                temperature=args.temperature,
            ))
            write_json(args.output, report)
            print(json.dumps(report, indent=2))
            if not report["summary"]["passed"]:
                sys.exit(1)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
