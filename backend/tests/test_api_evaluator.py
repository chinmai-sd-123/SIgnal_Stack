import pytest

from app.services.github import GitHubService


@pytest.mark.integration
def test_plugin_evaluate_end_to_end(client, monkeypatch):
    def fake_get_recursive_tree(self, repo_url):
        return ["README.md", "app/main.py", "tests/test_app.py"], "main"

    def fake_get_file_content(self, repo_url, file_path):
        if file_path.endswith("README.md"):
            return "# Demo Project\n"
        return "def handler():\n    return True\n"

    def fake_get_repo_metadata(self, repo_url):
        return {"is_fork": False}

    def fake_get_commit_history(self, repo_url, limit=50):
        return [
            {
                "message": "init",
                "author_name": "Dev",
                "author_email": "dev@example.com",
                "github_login": "dev",
                "date": "2024-01-01T00:00:00Z",
                "sha": "abc",
            }
        ]

    monkeypatch.setattr(GitHubService, "get_recursive_tree", fake_get_recursive_tree)
    monkeypatch.setattr(GitHubService, "get_file_content", fake_get_file_content)
    monkeypatch.setattr(GitHubService, "get_repo_metadata", fake_get_repo_metadata)
    monkeypatch.setattr(GitHubService, "get_commit_history", fake_get_commit_history)

    outcome_payload = {
        "title": "API Platform",
        "description": "Build REST API",
        "company": "SignalStack",
        "location": "Remote",
        "category": "Software Engineering",
        "job_type": "Full-time",
        "tasks": [
            {"name": "Implement API", "priority": "High", "weight": 0.6},
            {"name": "Add Tests", "priority": "Medium", "weight": 0.4},
        ],
    }
    outcome_resp = client.post("/outcomes", json=outcome_payload)
    assert outcome_resp.status_code == 200
    outcome_id = outcome_resp.json()["id"]

    outcome_get = client.get(f"/outcomes/{outcome_id}")
    assert outcome_get.status_code == 200
    outcome_obj = outcome_get.json()

    request_payload = {
        "request_id": "req-1",
        "outcome": outcome_obj,
        "proofs": [
            {
                "job_id": outcome_id,
                "candidate_id": "cand-1",
                "type": "github",
                "payload": {"repo_url": "https://github.com/acme/demo"},
            }
        ],
    }

    response = client.post("/plugin/evaluate", json=request_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["evaluation"]["job_id"] == outcome_id
