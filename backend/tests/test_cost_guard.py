import pytest

from app.pipeline.cost_guard import validate_eligibility, should_skip_llm


@pytest.mark.unit
def test_cost_guard_no_repos():
    result = validate_eligibility(candidate={}, repos=[])
    assert result.eligible is False
    assert result.reason == "NO_REPOS_FOUND"


@pytest.mark.unit
def test_cost_guard_evidence_required():
    repos = [{"manifest_present": True, "score": 0.5}]
    result = validate_eligibility(candidate={}, repos=repos, evidence_files=[])
    skip, reason = should_skip_llm(result)
    assert skip is True
    assert reason == "NO_EVIDENCE_EXTRACTED"
