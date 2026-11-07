from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .evaluators import (evaluate_conversation, evaluate_performance, evaluate_reliability,
                         evaluate_scoring_stability, summarize_performance)
from .io import load_jsonl
from .statistics import bootstrap_mean_interval, mean, stdev


def run_evaluation(dataset: str | Path, thresholds: dict[str, Any] | None = None) -> dict[str, Any]:
    limits = thresholds or {}
    cases = load_jsonl(dataset)
    conversations, scoring, reliability, performance = [], [], [], []
    for case in cases:
        kind = case.get("type")
        if kind == "conversation":
            conversations.append(evaluate_conversation(case))
        elif kind == "scoring":
            scoring.append(evaluate_scoring_stability(case, int(limits.get("min_repetitions", 3))))
        elif kind == "reliability":
            reliability.append(evaluate_reliability(case))
        elif kind == "performance":
            performance.append(evaluate_performance(case))
        else:
            raise ValueError(f"Case {case.get('id', '<unknown>')}: unsupported type {kind!r}")

    score_dims: dict[str, list[float]] = {}
    for result in scoring:
        for dimension, values in result.get("dimensions", {}).items():
            score_dims.setdefault(dimension, []).append(values["stddev"])
    stability = {dimension: {"mean_stddev": round(mean(values), 4),
                              "max_stddev": round(max(values),  default=0), "n_cases": len(values)}
                 for dimension, values in score_dims.items()}
    conversation_rate = (sum(r["passed"] for r in conversations) / len(conversations)
                         if conversations else 1.0)
    gates = {
        "conversation_pass_rate": conversation_rate >= float(limits.get("conversation_pass_rate_min", 0)),
        "scoring_sample_sizes": all(r.get("sample_size_sufficient", False) for r in scoring),
        "scoring_stability": all(
            values["max_stddev"] <= float(limits.get("scoring_stddev_max", float("inf")))
            for values in stability.values()),
        "reliability": all(r["passed"] for r in reliability),
        "latency_p95": (summarize_performance(performance)["p95_ms"] <=
                        float(limits.get("latency_p95_ms_max", float("inf")))
                        if performance else True),
    }
    return {
        "schema_version": "1.0",
        "run": {"timestamp": datetime.now(timezone.utc).isoformat(),
                "dataset": str(dataset), "case_count": len(cases)},
        "summary": {"passed": all(gates.values()), "gate_results": gates,
                    "conversation_pass_rate": round(conversation_rate, 4),
                    "conversation_cases": len(conversations),
                    "scoring_cases": len(scoring), "reliability_cases": len(reliability)},
        "conversation": conversations, "scoring_stability": scoring,
        "stability_summary": stability, "reliability": reliability,
        "performance": {"cases": performance, "summary": summarize_performance(performance)},
    }


def compare_reports(baseline: dict[str, Any], candidate: dict[str, Any],
                    max_dimension_delta: float = 1.0) -> dict[str, Any]:
    before = baseline.get("dimension_means", {})
    after = candidate.get("dimension_means", {})
    dimensions = sorted(set(before) | set(after))
    deltas = {name: round(float(after.get(name, 0)) - float(before.get(name, 0)), 4)
              for name in dimensions}
    regressions = {name: delta for name, delta in deltas.items() if abs(delta) > max_dimension_delta}
    return {"passed": not regressions, "baseline_label": baseline.get("label", "baseline"),
            "candidate_label": candidate.get("label", "candidate"),
            "dimension_deltas": deltas, "regressions": regressions,
            "threshold": max_dimension_delta}
