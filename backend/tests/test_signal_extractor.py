import pytest

from app.pipeline.signal_extractor import SignalExtractor


class FakeGitHub:
    def get_recursive_tree(self, repo_url):
        return ["app/main.py", "README.md"], "main"

    def get_file_content(self, repo_url, file_path):
        if file_path == "app/main.py":
            return "from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get('/health')\ndef health():\n    return {'ok': True}\n"
        if file_path == "README.md":
            return "# Auth API\n\nA small personal project."
        return ""


@pytest.mark.unit
def test_github_repo_takes_precedence_over_resume_artifact_link():
    extractor = SignalExtractor()
    extractor.github = FakeGitHub()

    evidence = extractor.extract_evidence(
        repo_url="https://github.com/candidate/auth-api",
        artifact_link="https://drive.google.com/file/d/resume/view",
        task_title="Build REST API",
        context="Candidate uploaded a resume too.",
    )

    assert evidence
    assert all(item.type != "work_artifact" for item in evidence)
    assert any(item.type in ("code_snippet", "repo_context") for item in evidence)


@pytest.mark.unit
def test_non_github_artifact_still_supported_when_no_repo_exists():
    extractor = SignalExtractor()

    evidence = extractor.extract_evidence(
        repo_url="",
        artifact_link="https://drive.google.com/file/d/work-sample/view",
        task_title="Create launch plan",
        context="Candidate explains their role.",
    )

    assert len(evidence) == 1
    assert evidence[0].type == "work_artifact"


@pytest.mark.unit
def test_extract_evidence_preserves_priority_order():
    extractor = SignalExtractor()
    extractor.github = FakeGitHub()

    evidence = extractor.extract_evidence(
        repo_url="https://github.com/candidate/auth-api",
        task_title="Build API health endpoint",
    )

    assert evidence[0].ref == "FILE:app/main.py"
