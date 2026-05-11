import pytest

from app.pipeline.identity_verifier import resolve_candidate_identities


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
