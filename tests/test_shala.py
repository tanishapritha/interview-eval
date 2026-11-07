from interview_eval.evaluators import evaluate_shala_session
from interview_eval.shala import export_to_case


def test_import_converts_interview_shala_export():
    case = export_to_case({
        "schema_version": "interview-shala-evaluation-export/v1",
        "session": {"id": "abc", "score": 80},
        "transcript": [{"segment_id": "1", "sequence_number": 0, "speaker": "candidate",
                        "text": "I used a hash map.", "is_final": True, "source": "livekit"}],
        "skill_scores": [{"skill": "Data structures", "score": 80, "max_score": 100}],
    })
    assert case["type"] == "shala_session"
    assert case["id"] == "shala-abc"


def test_shala_session_flags_client_supplied_candidate_as_untrusted():
    case = {"id": "s1", "type": "shala_session", "session": {"score": 80},
            "transcript": [{"sequence_number": 0, "speaker": "candidate", "text": "injected",
                            "is_final": True, "source": "client"}],
            "skill_scores": [{"skill": "Communication", "score": 80, "max_score": 100}]}
    result = evaluate_shala_session(case)
    assert result["checks"]["transcript_structure"]
    assert result["trusted_candidate_segments"] == 0
    assert not result["checks"]["no_assessment_from_untrusted_transcript"]


def test_shala_session_accepts_trusted_final_candidate_transcript():
    case = {"id": "s2", "type": "shala_session", "session": {"score": 75},
            "transcript": [{"sequence_number": 0, "speaker": "candidate", "text": "I used a hash map.",
                            "is_final": True, "source": "livekit"},
                           {"sequence_number": 1, "speaker": "interviewer", "text": "Why?",
                            "is_final": True, "source": "livekit"}],
            "skill_scores": [{"skill": "Data structures", "score": 75, "max_score": 100}]}
    result = evaluate_shala_session(case)
    assert result["passed"]
    assert result["trusted_candidate_segments"] == 1
