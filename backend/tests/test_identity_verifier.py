import pytest

from app.pipeline.identity_verifier import (
    calculate_authorship_from_identity,
    classify_identity_match,
    resolve_candidate_identities,
)
from app.pipeline.signal_extractor import SignalExtractor


@pytest.mark.unit
def test_identity_resolves_github_login():
    author_map = {
        "dev@example.com": {
            "commits": 3,
            "lines_added": 10,
            "name": "Dev User",
            "github_login": "devuser",
        }
    }

    candidate = {"github_username": "devuser"}
    identity = resolve_candidate_identities(candidate, author_map)

    assert "dev@example.com" in identity.matched_emails


@pytest.mark.unit
def test_claimed_github_handle_without_name_or_email_match_requires_review():
    author_map = {
        "chinmaisdinesh@gmail.com": {
            "commits": 14,
            "lines_added": 0,
            "name": "Chinmai SD",
            "github_login": "chinmai-sd-123",
        }
    }

    candidate = {
        "name": "johny",
        "email": "john@gmail.com",
        "github_username": "chinmai-sd-123",
    }

    identity = resolve_candidate_identities(candidate, author_map)
    auth_stats = calculate_authorship_from_identity(identity, author_map)
    status = classify_identity_match(candidate, identity, author_map)

    assert auth_stats["authorship_fraction"] == 1.0
    assert status["basis"] == "claimed_github_handle_only"
    assert status["requires_manual_review"] is True


@pytest.mark.unit
def test_name_or_email_match_verifies_authorship_identity():
    author_map = {
        "dev@example.com": {
            "commits": 4,
            "lines_added": 0,
            "name": "Dev User",
            "github_login": "devuser",
        }
    }

    candidate = {
        "name": "Dev User",
        "email": "candidate@example.com",
        "github_username": "devuser",
    }

    identity = resolve_candidate_identities(candidate, author_map)
    status = classify_identity_match(candidate, identity, author_map)

    assert status["basis"] == "verified"
    assert status["name_match"] is True


@pytest.mark.unit
def test_authorship_evidence_does_not_confirm_claimed_handle_only():
    extractor = SignalExtractor()

    commits = [
        {
            "author_name": "Chinmai SD",
            "author_email": "chinmaisdinesh@gmail.com",
            "github_login": "chinmai-sd-123",
        }
        for _ in range(14)
    ]
    author_map = {
        "chinmaisdinesh@gmail.com": {
            "commits": 14,
            "lines_added": 0,
            "name": "Chinmai SD",
            "github_login": "chinmai-sd-123",
        }
    }

    evidence = extractor.extract_authorship_signals(
        repo_url="https://github.com/chinmai-sd-123/SIgnal_Stack.git",
        candidate_name="johny",
        task_title="Productionize AI Backend Services",
        candidate_info={
            "candidate_name": "johny",
            "candidate_email": "john@gmail.com",
            "github_username": "chinmai-sd-123",
        },
        cached_commits=commits,
        cached_author_map=author_map,
    )

    assert "Identity Basis: claimed github handle only" in evidence.snippet
    assert "AUTHORSHIP NEEDS REVIEW" in evidence.snippet
    assert "AUTHORSHIP CONFIRMED" not in evidence.snippet
