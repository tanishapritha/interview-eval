from interview_eval.benchmark import validate_model_output


def test_model_output_requires_exact_quote_from_trusted_final_candidate():
    segments = [{"segment_id": "seg-1", "text": "I used a hash map.", "speaker": "candidate",
                 "is_final": True, "source": "livekit"}]
    raw = {"skills": [{"name": "Data structures", "score": 85, "confidence": 0.9,
                       "observations": [{"segment_id": "seg-1", "quote": "used a hash map",
                                         "polarity": "positive"}]}]}
    result = validate_model_output(raw, segments)
    assert result["dimensions"]["Data structures"] == 85
    assert result["valid_quotes"] == 1


def test_model_output_rejects_fabricated_quote():
    segments = [{"segment_id": "seg-1", "text": "I used a list.", "speaker": "candidate",
                 "is_final": True, "source": "livekit"}]
    raw = {"skills": [{"name": "Data structures", "score": 85, "confidence": 0.9,
                       "observations": [{"segment_id": "seg-1", "quote": "I used a tree",
                                         "polarity": "positive"}]}]}
    try:
        validate_model_output(raw, segments)
    except ValueError as exc:
        assert "verifiable quote" in str(exc)
    else:
        raise AssertionError("fabricated quote must be rejected")
