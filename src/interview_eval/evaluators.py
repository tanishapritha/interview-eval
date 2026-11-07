from __future__ import annotations

from collections import Counter
from typing import Any

from .statistics import mean, percentile, stdev


def evaluate_conversation(case: dict[str, Any]) -> dict[str, Any]:
    turns = case.get("turns", [])
    interviewer = [t for t in turns if t.get("role") == "interviewer"]
    transcript_text = " ".join(str(t.get("text", "")) for t in turns).lower()
    missing_terms = [term for term in case.get("required_terms", []) if term.lower() not in transcript_text]
    questions = [str(t.get("text", "")).strip().lower() for t in interviewer]
    repeated = [q for q, count in Counter(questions).items() if count > 1 and q]
    checks = {
        "minimum_interviewer_questions": len(interviewer) >= int(case.get("min_interviewer_questions", 1)),
        "required_terms_present": not missing_terms,
        "no_repeated_interviewer_turns": not (case.get("forbidden_repetition", False) and repeated),
    }
    return {"case_id": case["id"], "checks": checks, "passed": all(checks.values()),
            "missing_terms": missing_terms, "repeated_turns": repeated,
            "interviewer_turns": len(interviewer)}


def evaluate_scoring_stability(case: dict[str, Any], min_repetitions: int = 3) -> dict[str, Any]:
    repetitions = case.get("repetitions", [])
    if not repetitions:
        return {"case_id": case["id"], "passed": False, "error": "no scoring repetitions"}
    dimensions = sorted({key for row in repetitions for key in row})
    metrics = {}
    for dimension in dimensions:
        values = [float(row[dimension]) for row in repetitions if dimension in row]
        metrics[dimension] = {"mean": round(mean(values), 4), "stddev": round(stdev(values), 4),
                              "min": min(values), "max": max(values), "n": len(values)}
    enough = len(repetitions) >= min_repetitions
    return {"case_id": case["id"], "passed": enough, "sample_size": len(repetitions),
            "sample_size_sufficient": enough, "dimensions": metrics}


def evaluate_reliability(case: dict[str, Any]) -> dict[str, Any]:
    transcript = case.get("transcript")
    output = case.get("scorer_output")
    errors = []
    if not isinstance(transcript, dict) or not isinstance(transcript.get("turns"), list):
        errors.append("transcript.turns must be a list")
    else:
        for index, turn in enumerate(transcript["turns"]):
            if turn.get("role") not in {"candidate", "interviewer"}:
                errors.append(f"turn {index}: unsupported role")
            if not isinstance(turn.get("text"), str) or not turn["text"].strip():
                errors.append(f"turn {index}: text must be a non-empty string")
    if not isinstance(output, dict) or not isinstance(output.get("dimensions"), dict):
        errors.append("scorer_output.dimensions must be an object")
    elif any(not isinstance(value, (int, float)) for value in output["dimensions"].values()):
        errors.append("scorer dimension values must be numeric")
    if isinstance(output, dict) and "overall" in output and not isinstance(output["overall"], (int, float)):
        errors.append("scorer_output.overall must be numeric")
    return {"case_id": case["id"], "passed": not errors, "errors": errors}


def evaluate_performance(case: dict[str, Any]) -> dict[str, Any]:
    stages = {name: float(case.get(f"{name}_ms", 0)) for name in ("stt", "llm", "tts")}
    total = sum(stages.values())
    return {"case_id": case["id"], "stages_ms": stages, "total_ms": total,
            "input_tokens": int(case.get("input_tokens", 0)),
            "output_tokens": int(case.get("output_tokens", 0)),
            "interview_seconds": float(case.get("interview_seconds", 0))}


def summarize_performance(results: list[dict[str, Any]]) -> dict[str, Any]:
    totals = [row["total_ms"] for row in results]
    return {"n": len(totals), "mean_ms": round(mean(totals), 2),
            "p50_ms": round(percentile(totals, 50), 2),
            "p95_ms": round(percentile(totals, 95), 2),
            "total_input_tokens": sum(row["input_tokens"] for row in results),
            "total_output_tokens": sum(row["output_tokens"] for row in results),
            "stage_mean_ms": {stage: round(mean([r["stages_ms"][stage] for r in results]), 2)
                              for stage in ("stt", "llm", "tts")}}
