# Interview Eval

[![Evaluation CI](https://github.com/tanishapritha/interview-eval/actions/workflows/eval.yml/badge.svg)](https://github.com/tanishapritha/interview-eval/actions/workflows/eval.yml)

A reproducible Python evaluation harness for conversational interview agents, built alongside [Interview Shala](https://github.com/tanishapritha/interview-shala). It checks trusted transcript integrity, score stability, evidence citations, and voice pipeline latency.

## Quickstart

Requires Python 3.11+.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
interview-eval run --dataset datasets/golden/demo.jsonl --output reports/latest.json
```

The offline suite needs no API key, database, or network access. Fixtures are synthetic.

## Evaluate a real Interview Shala session

Interview Shala exposes an owner-authenticated export endpoint:

`GET /api/v1/sessions/{session_id}/evaluation-export`

It exports only that user's session, includes transcript provenance, and is available after completion. Save the JSON response locally; **do not commit real candidate transcripts or export files to a public repository**.

```bash
interview-eval import-shala --input shala-session.json --output datasets/local/session.jsonl
interview-eval run --dataset datasets/local/session.jsonl --output reports/session-integrity.json
```

The importer preserves source labels. Only final candidate segments with `source=livekit` are considered trusted evidence. Client-submitted transcript segments are never eligible for model scoring.

## Repeat the production-style scorer

The live benchmark calls OpenRouter repeatedly using the same evidence-grounded scoring contract used by Interview Shala. It validates each score against an exact quote from a final trusted candidate segment, then reports per-skill mean, sample standard deviation, min/max, valid and invalid citations, latency, token usage, and deltas against the saved session assessment.

```bash
# Set OPENROUTER_API_KEY in your shell; never put it in a committed file.
# Optional: set OPENROUTER_MODEL to pin a different model.
interview-eval benchmark --dataset datasets/local/session.jsonl --runs 5 \\
  --temperature 0.1 --output reports/benchmark.json
```

This makes real provider calls and incurs provider usage. Use a small number of sessions and repetitions first. Benchmark reports contain model scores and timing; keep them private if they relate to real candidate data. The benchmark is a repeated-scorer consistency experiment, not a ground-truth accuracy test. Accuracy and fairness require human-labelled reference scores.

## Evaluation suites

| Suite | Checks |
| --- | --- |
| Interview Shala integrity | Transcript structure/order, provenance, score ranges, and whether untrusted client speech could be the sole basis for an assessment |
| Conversation | Minimum interviewer turns, required terms, repeated interviewer turns |
| Score stability | Per-dimension mean, sample standard deviation, min/max, repetition count |
| Reliability | Transcript role/text shape and numeric scorer output validation |
| Evidence validation | Exact quote must exist in the referenced final LiveKit candidate segment |
| Performance | STT/LLM/TTS stage timing, total latency, P50/P95, token totals |

Keyword presence is a lightweight smoke check, **not** a semantic relevance judge. Exact quote verification establishes provenance, not whether the quote logically supports the score.

## Dataset formats

JSONL rows support `conversation`, `scoring`, `reliability`, `performance`, and `shala_session`. See `datasets/golden/demo.jsonl` and `tests` for examples. Keep real candidate data local and de-identified where possible.

## Configuration and interpretation

Edit `configs/thresholds.json` for offline release gates. Reports include timestamps, dataset path, case-level outcomes, and gate results. P95 from a tiny fixture set is a smoke metric, not a production SLO. Small repeated samples are descriptive, not conclusive. Provider cost estimation is omitted until a dated rate card is configured.

## Baseline comparison

```bash
interview-eval compare --baseline examples/baseline.json \\
  --candidate examples/candidate.json --max-delta 0.5
```

A score shift is a regression candidate, not proof of quality loss. Compare the same transcripts (paired evaluation) and review case-level changes.

## CI

GitHub Actions runs unit tests and the offline golden evaluation on pushes, pull requests, and manual dispatch. No provider secrets are needed in CI. Live benchmarks are opt-in and should be run locally or in a separate secured workflow with explicit spend limits.

## Roadmap

- [x] Owner-authenticated Interview Shala session export.
- [x] Local importer preserving transcript provenance.
- [x] Repeated OpenRouter scoring benchmark with exact quote validation.
- [ ] Human-labelled reference set and evaluator calibration.
- [ ] Paired prompt/model experiment reports with confidence intervals.
- [ ] Provider-specific dated rate cards and cost-per-interview estimates.
- [ ] Semantic interviewer follow-up evaluation.

## License

MIT
