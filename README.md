# Interview Eval

[![Evaluation CI](https://github.com/tanishapritha/interview-eval/actions/workflows/eval.yml/badge.svg)](https://github.com/tanishapritha/interview-eval/actions/workflows/eval.yml)

A small, reproducible Python evaluation harness for conversational interview agents. It is designed alongside [Interview Shala](https://github.com/tanishapritha/interview-shala), whose voice pipeline uses LiveKit Agents, Deepgram STT, an OpenRouter-compatible LLM, Cartesia TTS, and trusted worker-side transcript ingestion.

**Current scope:** deterministic, offline evaluation of transcript-level conversation checks, repeated-score stability, transcript/scorer schema reliability, and stage latency/token summaries. This is an evaluation foundation, not a claim that a production interviewer scorer has already been integrated.

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

No API key, database, or network connection is needed for the offline suite. The demo dataset is synthetic and intentionally small.

## What is evaluated?

| Suite | Current behavior |
| --- | --- |
| Conversation | Minimum interviewer turns, required terms, exact repeated interviewer turns |
| Score stability | Per-dimension mean, sample standard deviation, min/max, repetition count |
| Reliability | Transcript role/text shape and numeric scorer output validation |
| Performance | STT/LLM/TTS stage timing, total latency, P50/P95, token totals |

The checks are intentionally transparent and deterministic. Keyword presence is a lightweight smoke check, **not** a semantic relevance judge. A future semantic evaluator should be calibrated against human annotations before it is used as a release gate.

## Dataset format

Each JSONL row is an independent case. Supported `type` values:

- `conversation`: `turns`, `required_terms`, `min_interviewer_questions`, `forbidden_repetition`.
- `scoring`: `repetitions`, each a mapping from score dimension to numeric score.
- `reliability`: `transcript.turns` and `scorer_output.dimensions`.
- `performance`: `stt_ms`, `llm_ms`, `tts_ms`, token counts, and interview duration.

See `datasets/golden/demo.jsonl`. Keep real candidate data out of public fixtures; use synthetic or explicitly consented, de-identified examples.

## Configuration

Edit `configs/thresholds.json`:

- `conversation_pass_rate_min`: minimum fraction of conversation cases passing.
- `scoring_stddev_max`: maximum allowed per-dimension standard deviation averaged across cases.
- `min_repetitions`: minimum repeated scoring runs per scoring case.
- `latency_p95_ms_max`: maximum P95 total stage latency in milliseconds.
- `max_dimension_delta`: threshold used by report comparison.

The runner writes a JSON report with timestamp, dataset path, case count, per-case outcomes, summary metrics, and gate results. The report timestamp is intentionally recorded; all other inputs are explicit. For byte-for-byte artifact reproducibility, normalize or omit the timestamp in downstream tooling.

## Baseline comparison

The comparison command accepts compact JSON summaries with dimension means:

```json
{
  "label": "prompt-v1",
  "dimension_means": {"technical": 3.8, "communication": 4.1}
}
```

```bash
interview-eval compare --baseline examples/baseline.json \\
  --candidate examples/candidate.json --max-delta 0.5
```

A dimension whose absolute delta exceeds the configured threshold is reported as a regression candidate. A score shift is not automatically evidence of quality loss: review case-level changes and human annotations before release decisions.

## Reproducibility and statistical notes

- Version datasets and evaluator code with Git.
- Record model/provider, prompt version, temperature, seed, repetition count, and pricing snapshot when adding live adapters.
- Compare prompt/model versions on the same cases (paired evaluation).
- Treat small samples as descriptive; the included bootstrap helper uses a fixed seed but does not make an underpowered sample conclusive.
- P95 from a small fixture set is a smoke metric, not a production SLO.
- Cost estimation is deliberately not enabled until provider-specific rate cards and token accounting are supplied.

## CI

GitHub Actions runs pytest and the offline golden evaluation on pushes, pull requests, and manual dispatch. No provider secrets are required. Live model evaluations should be a separate opt-in workflow with pinned model identifiers and explicit spend limits.

## Roadmap

- [ ] Adapter contract for Interview Shala worker transcripts and evaluator outputs.
- [ ] Semantic follow-up/relevance judging calibrated against human-labelled cases.
- [ ] Paired baseline/candidate scoring with confidence intervals and per-case diffs.
- [ ] Provider-specific STT/LLM/TTS cost accounting with dated rate-card snapshots.
- [ ] Opt-in live benchmark runner with retries, timeout accounting, and spend caps.
- [ ] Dimension drift guards based on labelled reference sets.

## Relationship to Interview Shala

Interview Shala currently persists trusted worker-generated transcript turns and maintains a separate trust boundary for client-supplied transcript material. This repo consumes evaluation fixtures rather than reaching into its database or production APIs. The adapter boundary is a planned integration so the harness can be run safely against exported, consented test transcripts.

## License

MIT
