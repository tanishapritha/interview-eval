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
    elif any(not isinstance(value, (int, float)) or isinstance(value, bool)
             for value in output["dimensions"].values()):
        errors.append("scorer dimension values must be numeric")
    if isinstance(output, dict) and "overall" in output and (
        not isinstance(output["overall"], (int, float)) or isinstance(output["overall"], bool)
    ):
        errors.append("scorer_output.overall must be numeric")
    return {"case_id": case["id"], "passed": not errors, "errors": errors}


def evaluate_shala_session(case: dict[str, Any]) -> dict[str, Any]:
    """Check an owned Interview Shala export without treating client text as evidence."""
    transcript = case.get("transcript")
    session = case.get("session")
    skills = case.get("skill_scores", [])
    errors: list[str] = []
    if not isinstance(transcript, list):
        transcript = []
        errors.append("transcript must be an array")
    if not isinstance(session, dict):
        session = {}
        errors.append("session must be an object")
    sequence_numbers = []
    trusted_candidates = 0
    client_candidates = 0
    for index, segment in enumerate(transcript):
        if not isinstance(segment, dict):
            errors.append(f"segment {index} must be an object")
            continue
        sequence = segment.get("sequence_number")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            errors.append(f"segment {index} has an invalid sequence number")
        else:
            sequence_numbers.append(sequence)
        if segment.get("speaker") not in {"candidate", "interviewer", "system"}:
            errors.append(f"segment {index} has an invalid speaker")
        if not isinstance(segment.get("text"), str) or not segment["text"].strip():
            errors.append(f"segment {index} has empty text")
        if not isinstance(segment.get("is_final"), bool):
            errors.append(f"segment {index} has an invalid finality flag")
        if segment.get("speaker") == "candidate":
            if segment.get("source") == "livekit" and segment.get("is_final") is True:
                trusted_candidates += 1
            elif segment.get("source") == "client":
                client_candidates += 1
    unique_ordered = len(sequence_numbers) == len(set(sequence_numbers)) and sequence_numbers == sorted(sequence_numbers)
    if not unique_ordered:
        errors.append("transcript sequence numbers must be unique and ordered")
    score = session.get("score")
    score_valid = score is None or (
        isinstance(score, (int, float)) and not isinstance(score, bool) and 0 <= score <= 100
    )
    if not score_valid:
        errors.append("session score must be null or between 0 and 100")
    skills_valid = isinstance(skills, list)
    if skills_valid:
        for index, skill in enumerate(skills):
            if not isinstance(skill, dict):
                skills_valid = False
                errors.append(f"skill score {index} must be an object")
                continue
            value, maximum = skill.get("score"), skill.get("max_score", 100)
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or isinstance(maximum, bool) or not isinstance(maximum, (int, float))
                    or maximum <= 0 or not 0 <= value <= maximum):
                skills_valid = False
                errors.append(f"skill score {index} is outside its valid range")
    else:
        errors.append("skill_scores must be an array")
    checks = {
        "transcript_structure": not any("segment" in error or "sequence" in error
                                        for error in errors),
        "score_range": score_valid and skills_valid,
        "no_assessment_from_untrusted_transcript": not (
            client_candidates > 0 and (score is not None or bool(skills))
            and trusted_candidates == 0
        ),
    }
    return {
        "case_id": case["id"],
        "passed": all(checks.values()),
        "checks": checks,
        "errors": errors,
        "trusted_candidate_segments": trusted_candidates,
        "untrusted_candidate_segments": client_candidates,
        "transcript_segments": len(transcript),
        "score_present": score is not None,
        "skill_count": len(skills) if isinstance(skills, list) else 0,
    }


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
