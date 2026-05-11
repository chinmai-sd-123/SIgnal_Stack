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


@pytest.mark.unit
def test_personal_project_not_crushed_for_missing_tests_and_ci():
    signals = {
        "authorship_fraction": 0.6,
        "valid_repo": 1.0,
        "web_framework": 1.0,
        "recent_activity_score": 1.0,
        "readme_quality_score": 0.6,
        "commit_count": 1.0,
        "tests_present": 0.0,
        "ci_cd_present": 0.0,
    }

    result = score_candidate(signals)

    assert result.capped_score >= 0.4
    assert "low_authorship" not in result.risk_flags


@pytest.mark.unit
def test_low_but_nonzero_authorship_is_soft_penalty_not_hard_cap():
    signals = {
        "authorship_fraction": 0.1,
        "valid_repo": 1.0,
        "web_framework": 1.0,
        "recent_activity_score": 1.0,
        "readme_quality_score": 0.6,
        "commit_count": 1.0,
    }

    result = score_candidate(signals)

    assert 0.2 < result.capped_score < result.normalized_score
    assert "low_authorship" in result.risk_flags


@pytest.mark.unit
def test_ci_present_alias_scores_without_duplicate_weight_penalty():
    result = score_candidate({"ci_present": 1.0, "valid_repo": 1.0})

    assert result.score_breakdown["ci_present"]["weight"] == 0.04
    assert result.score_breakdown["ci_present"]["contribution"] == 0.04
