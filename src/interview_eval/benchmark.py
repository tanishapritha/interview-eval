from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from .statistics import mean, stdev


SYSTEM_PROMPT = (
    "Return only valid JSON. Be rigorous and evidence-bound. "
    "Do not infer ability from confidence, accent, verbosity, or demographic cues."
)


def _eligible_segments(case: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        segment for segment in case.get("transcript", [])
        if segment.get("speaker") == "candidate"
        and segment.get("is_final") is True
        and segment.get("source") == "livekit"
        and isinstance(segment.get("text"), str)
        and segment["text"].strip()
    ]


def validate_model_output(raw: Any, segments: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(raw, dict) or not isinstance(raw.get("skills"), list):
        raise ValueError("model response must contain a skills array")
    eligible = {str(segment.get("segment_id")): segment for segment in segments}
    dimensions: dict[str, float] = {}
    confidence_weights: dict[str, float] = {}
    valid_quotes = 0
    invalid_quotes = 0
    for item in raw["skills"][:20]:
        if not isinstance(item, dict):
            invalid_quotes += 1
            continue
        name = str(item.get("name", "")).strip()[:120]
        score = item.get("score")
        confidence = item.get("confidence")
        if (not name or isinstance(score, bool) or not isinstance(score, (int, float))
                or not 0 <= score <= 100 or isinstance(confidence, bool)
                or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1):
            invalid_quotes += 1
            continue
        observations = item.get("observations", [])
        if not isinstance(observations, list):
            invalid_quotes += 1
            continue
        verified = []
        for observation in observations[:20]:
            if not isinstance(observation, dict):
                invalid_quotes += 1
                continue
            source = eligible.get(str(observation.get("segment_id")))
            quote = observation.get("quote")
            if (source is not None and isinstance(quote, str) and quote.strip()
                    and quote in source["text"]
                    and observation.get("polarity") in {"positive", "negative", "neutral"}):
                valid_quotes += 1
                verified.append(observation)
            else:
                invalid_quotes += 1
        if verified:
            dimensions[name] = float(score)
            confidence_weights[name] = float(confidence)
    if not dimensions:
        raise ValueError("no skill score had a verifiable quote from final LiveKit candidate speech")
    return {
        "dimensions": dimensions,
        "overall": (
            sum(dimensions[name] * confidence_weights[name] for name in dimensions)
            / sum(confidence_weights.values())
        ),
        "valid_quotes": valid_quotes,
        "invalid_quotes": invalid_quotes,
    }


async def _score_once(
    client: httpx.AsyncClient, *, api_key: str, model: str,
    segments: list[dict[str, Any]], temperature: float,
) -> dict[str, Any]:
    prompt = {
        "task": (
            "Assess interview answer quality, technical correctness, reasoning, depth and communication. "
            "Only assess what the candidate actually said. Scores are 0-100; confidence is 0-1. "
            "Each observation must cite an exact substring from one candidate segment by segment_id. "
            "Never cite interviewer speech. Omit skills without direct evidence."
        ),
        "transcript": [
            {"segment_id": segment["segment_id"], "text": segment["text"]}
            for segment in segments
        ],
        "required_json_shape": {
            "skills": [{
                "name": "string", "score": 0, "confidence": 0.0, "rationale": "string",
                "observations": [{
                    "segment_id": "uuid", "quote": "exact substring",
                    "polarity": "positive|negative|neutral",
                    "evidence_type": "string", "explanation": "string", "confidence": 0.0,
                }],
            }],
            "next_action": "string",
        },
    }
    started = time.perf_counter()
    response = await client.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(prompt)},
            ],
        },
    )
    response.raise_for_status()
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    result = validate_model_output(parsed, segments)
    result["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    result["usage"] = payload.get("usage", {})
    return result


async def run_benchmark(
    cases: list[dict[str, Any]], *, api_key: str | None = None,
    model: str | None = None, repetitions: int = 3, temperature: float = 0.1,
) -> dict[str, Any]:
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    model_name = model or os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
    if not key:
        raise ValueError("Set OPENROUTER_API_KEY before running a live benchmark")
    if repetitions < 2 or repetitions > 20:
        raise ValueError("repetitions must be between 2 and 20")
    output = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
        for case in cases:
            segments = _eligible_segments(case)
            if not segments:
                output.append({"case_id": case["id"], "passed": False,
                               "error": "no final trusted LiveKit candidate transcript"})
                continue
            runs = []
            for index in range(repetitions):
                try:
                    result = await _score_once(
                        client, api_key=key, model=model_name, segments=segments,
                        temperature=temperature,
                    )
                    result["repetition"] = index + 1
                    runs.append(result)
                except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
                    runs.append({"repetition": index + 1, "error": str(exc)[:300]})
            successful = [item for item in runs if "dimensions" in item]
            dimension_names = sorted({name for item in successful for name in item["dimensions"]})
            stability = {}
            for name in dimension_names:
                values = [item["dimensions"][name] for item in successful if name in item["dimensions"]]
                stability[name] = {
                    "mean": round(mean(values), 3),
                    "stddev": round(stdev(values), 3),
                    "min": min(values),
                    "max": max(values),
                    "n": len(values),
                }
            baseline = {
                item.get("skill"): float(item.get("score", 0))
                for item in case.get("skill_scores", []) if item.get("skill")
            }
            deltas = {
                name: round(values["mean"] - baseline[name], 3)
                for name, values in stability.items() if name in baseline
            }
            output.append({
                "case_id": case["id"],
                "passed": len(successful) == repetitions,
                "requested_repetitions": repetitions,
                "successful_repetitions": len(successful),
                "stability": stability,
                "baseline_deltas_vs_saved_session": deltas,
                "valid_quotes": sum(item.get("valid_quotes", 0) for item in successful),
                "invalid_quotes": sum(item.get("invalid_quotes", 0) for item in successful),
                "latency_mean_ms": round(mean([item["latency_ms"] for item in successful]), 2),
                "token_usage": {
                    "prompt_tokens": sum(item.get("usage", {}).get("prompt_tokens", 0)
                                         for item in successful),
                    "completion_tokens": sum(item.get("usage", {}).get("completion_tokens", 0)
                                             for item in successful),
                },
                "runs": runs,
            })
    return {
        "schema_version": "1.0",
        "run": {"timestamp": datetime.now(timezone.utc).isoformat(), "model": model_name,
                "temperature": temperature, "repetitions": repetitions},
        "summary": {
            "cases": len(output),
            "passed": bool(output) and all(item["passed"] for item in output),
            "successful_cases": sum(item["passed"] for item in output),
            "invalid_evidence_quotes": sum(item.get("invalid_quotes", 0) for item in output),
        },
        "cases": output,
    }
