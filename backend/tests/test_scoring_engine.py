import pytest

from app.pipeline.scoring_engine import score_candidate


@pytest.mark.unit
def test_scoring_caps_for_fork_and_authorship():
    signals = {
        "authorship_fraction": 0.1,
        "tests_present": 1.0,
        "ci_cd_present": 1.0,
        "deployment_ready": 1.0,
        "is_fork": 1.0,
        "fork_is_unmodified": 1.0,
    }

    result = score_candidate(signals)
    assert result.capped_score <= 0.2
    assert "fork_unmodified" in result.risk_flags
    assert "low_authorship" in result.risk_flags
