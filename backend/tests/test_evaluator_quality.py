import pytest

from app.pipeline.evaluator import _candidate_quality


@pytest.mark.unit
def test_candidate_quality_separates_capability_from_verification():
    quality = _candidate_quality(
        {
            "authorship_fraction": 0.1,
            "valid_repo": 1.0,
            "web_framework": 1.0,
            "recent_activity_score": 1.0,
            "readme_quality_score": 0.6,
            "tests_present": 0.0,
            "ci_cd_present": 0.0,
        },
        capability_score=0.82,
    )

    assert quality["capability_score"] == 0.82
    assert quality["verification_status"] == "unverified"
    assert "low_authorship" in quality["risk_flags"]
    assert quality["production_readiness"] < 0.5


@pytest.mark.unit
def test_candidate_quality_flags_unmodified_fork_as_conflict():
    quality = _candidate_quality(
        {
            "authorship_fraction": 0.8,
            "is_fork": 1.0,
            "fork_is_unmodified": 1.0,
            "tests_present": 1.0,
            "ci_cd_present": 1.0,
        },
        capability_score=0.9,
    )

    assert quality["verification_status"] == "conflict"
    assert "fork_unmodified" in quality["risk_flags"]
    assert quality["confidence_rating"] == "Low"
