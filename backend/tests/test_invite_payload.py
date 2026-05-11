import pytest

from app.models.invite import InviteSubmission
from app.routes.invite import _proof_payload_for_submission


@pytest.mark.unit
def test_invite_proof_payload_includes_github_username_for_authorship_verification():
    submission = InviteSubmission(
        id="sub-1",
        candidate_name="Candidate Dev",
        candidate_email="candidate@example.com",
        github_username="candidate-dev",
        repo_url="https://github.com/candidate-dev/auth-api",
        resume_url="https://drive.google.com/resume",
        leetcode_username="leetcode-dev",
        linkedin_url="https://linkedin.com/in/candidate-dev",
        context="Built the backend API.",
    )

    payload = _proof_payload_for_submission(submission)

    assert payload["github_username"] == "candidate-dev"
    assert payload["repo_url"] == "https://github.com/candidate-dev/auth-api"
    assert payload["artifact_link"] == ""
    assert payload["resume_url"] == "https://drive.google.com/resume"
    assert payload["source"] == "invite"


@pytest.mark.unit
def test_invite_proof_payload_uses_resume_as_artifact_only_without_repo():
    submission = InviteSubmission(
        id="sub-2",
        candidate_name="Candidate Dev",
        candidate_email="candidate@example.com",
        github_username="candidate-dev",
        repo_url="",
        resume_url="https://drive.google.com/resume",
    )

    payload = _proof_payload_for_submission(submission)

    assert payload["github_username"] == "candidate-dev"
    assert payload["repo_url"] == ""
    assert payload["artifact_link"] == "https://drive.google.com/resume"
