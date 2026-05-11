import pytest

from app.services.llm_summarizer import validate_response_schema, generate_deterministic_summary


@pytest.mark.unit
def test_validate_response_schema():
    valid = {
        "summary": "ok",
        "key_strengths": ["a"],
        "concerns": ["b"],
        "confidence_reason": "test",
    }
    assert validate_response_schema(valid) is True


@pytest.mark.unit
def test_deterministic_summary_includes_risk():
    signals = {
        "authorship_fraction": {"value": 0.1},
        "tests_present": {"value": 0.2},
    }
    scoring = {"capped_score": 0.2, "risk_flags": ["low_authorship"]}
    summary = generate_deterministic_summary(signals, scoring)
    assert "low authorship" in " ".join(summary["concerns"]).lower()
