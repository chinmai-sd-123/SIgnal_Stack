import pytest

from app.pipeline.evaluator import _candidate_quality
from app.schemas.evaluation import CandidateScore
from app.schemas.proof import Evidence


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


@pytest.mark.unit
def test_candidate_score_can_carry_candidate_specific_evidence():
    score = CandidateScore(
        candidate_id="candidate-b",
        score=0.62,
        justification="Relevant implementation found.",
        evidence=[
            Evidence(
                type="code_snippet",
                ref="FILE:candidate_b/app.py",
                snippet="candidate b implementation",
                source_url="https://github.com/candidate-b/repo/blob/main/app.py",
            )
        ],
    )

    dumped = score.model_dump()

    assert dumped["evidence"][0]["ref"] == "FILE:candidate_b/app.py"
    assert "candidate-b/repo" in dumped["evidence"][0]["source_url"]
