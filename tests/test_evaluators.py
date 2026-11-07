from interview_eval.evaluators import (evaluate_conversation, evaluate_reliability,
                                       evaluate_scoring_stability)
from interview_eval.runner import run_evaluation


def test_conversation_flags_repeated_interviewer_question():
    case = {"id": "x", "turns": [{"role": "interviewer", "text": "Tell me about Python"},
            {"role": "candidate", "text": "I use Python"},
            {"role": "interviewer", "text": "Tell me about Python"}],
            "required_terms": ["Python"], "min_interviewer_questions": 2,
            "forbidden_repetition": True}
    result = evaluate_conversation(case)
    assert not result["passed"]
    assert not result["checks"]["no_repeated_interviewer_turns"]


def test_scoring_stability_uses_sample_standard_deviation():
    case = {"id": "s", "repetitions": [{"technical": 3}, {"technical": 3}, {"technical": 5}]}
    result = evaluate_scoring_stability(case)
    assert result["dimensions"]["technical"]["n"] == 3
    assert result["dimensions"]["technical"]["stddev"] > 0


def test_reliability_rejects_bad_roles():
    result = evaluate_reliability({"id": "r", "transcript": {"turns": [
        {"role": "system", "text": "unexpected"}]}, "scorer_output": {"dimensions": {}}})
    assert not result["passed"]


def test_demo_dataset_runs():
    report = run_evaluation("datasets/golden/demo.jsonl", {"min_repetitions": 3})
    assert report["run"]["case_count"] == 6
    assert report["summary"]["passed"]
