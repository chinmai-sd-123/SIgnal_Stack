import pytest

from app.services.github import GitHubService


@pytest.mark.integration
def test_feedback_records_learning_history(client, monkeypatch):
    def fake_get_recursive_tree(self, repo_url):
        return ["README.md", "app/main.py", "tests/test_app.py"], "main"

    def fake_get_file_content(self, repo_url, file_path):
        if file_path.endswith("README.md"):
            return "# Demo Project\nA working FastAPI service."
        return "from fastapi import FastAPI\napp = FastAPI()\n"

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

    outcome_resp = client.post(
        "/outcomes",
        json={
            "title": "API Platform",
            "description": "Build REST API",
            "company": "SignalStack",
            "location": "Remote",
            "category": "Software Engineering",
            "job_type": "Full-time",
            "tasks": [{"name": "Implement API", "priority": "High", "weight": 1.0}],
        },
    )
    assert outcome_resp.status_code == 200
    outcome_id = outcome_resp.json()["id"]

    outcome_obj = client.get(f"/outcomes/{outcome_id}").json()
    eval_resp = client.post(
        "/plugin/evaluate",
        json={
            "request_id": "req-feedback",
            "outcome": outcome_obj,
            "proofs": [
                {
                    "job_id": outcome_id,
                    "candidate_id": "cand-1",
                    "type": "github",
                    "payload": {"repo_url": "https://github.com/acme/demo"},
                }
            ],
        },
    )
    assert eval_resp.status_code == 200

    feedback_resp = client.post(
        "/plugin/feedback",
        json={
            "job_id": outcome_id,
            "evaluation_id": "eval_123",
            "result": "success",
            "metrics": {
                "action_taken": "hire",
                "selected_candidates": ["cand-1"],
                "rejected_candidates": [],
                "selected_candidate": "cand-1",
            },
        },
    )
    assert feedback_resp.status_code == 200
    assert feedback_resp.json()["feedback_id"]
    assert feedback_resp.json()["changes"] != ["No signals found to update"]

    feedback_list = client.get("/admin/feedback").json()
    saved_feedback = next(item for item in feedback_list if item["job_id"] == outcome_id)
    assert saved_feedback["id"] == feedback_resp.json()["feedback_id"]

    history = client.get("/admin/weight-history").json()["history"]
    assert any(item["feedback_id"] == feedback_resp.json()["feedback_id"] for item in history)

    signal_weights = client.get("/admin/signal-weights").json()
    assert signal_weights

    task_history_resp = client.get("/admin/task-weight-history")
    assert task_history_resp.status_code == 200
    assert isinstance(task_history_resp.json(), list)

    task_feedback_resp = client.post(
        "/feedback/task-weight",
        json={
            "job_id": outcome_id,
            "task_name": "Implement API",
            "direction": "penalize",
            "reason": "Needs stronger API implementation evidence",
        },
    )
    assert task_feedback_resp.status_code == 200
    task_feedback = task_feedback_resp.json()
    assert task_feedback["status"] == "success"
    assert task_feedback["new_weights"]["Implement API"] == 0.85

    task_history = client.get("/admin/task-weight-history").json()
    matching_history = [
        item for item in task_history
        if item["feedback_source_job_id"] == outcome_id and item["task_name"] == "Implement API"
    ]
    assert matching_history
    assert matching_history[0]["outcome_title"] == "API Platform"
    assert matching_history[0]["reason"] == "Needs stronger API implementation evidence"

    audit_logs = client.get("/admin/audit-logs").json()
    assert any(log["entity_type"] == "task_feedback" and log["entity_id"] == outcome_id for log in audit_logs)

    invalid_task_resp = client.post(
        "/feedback/task-weight",
        json={
            "job_id": outcome_id,
            "task_name": "Missing task",
            "direction": "boost",
            "reason": "Should fail clearly",
        },
    )
    assert invalid_task_resp.status_code == 400
    assert "Missing task" in invalid_task_resp.json()["detail"]


@pytest.mark.integration
def test_task_feedback_boost_at_max_does_not_reduce_weight(client):
    outcome_resp = client.post(
        "/outcomes",
        json={
            "title": "Max Weight Outcome",
            "description": "Check stable boost behavior",
            "company": "SignalStack",
            "location": "Remote",
            "category": "Software Engineering",
            "job_type": "Full-time",
            "tasks": [{"name": "Already Max", "priority": "High", "weight": 1.0}],
        },
    )
    assert outcome_resp.status_code == 200
    outcome_id = outcome_resp.json()["id"]

    task_feedback_resp = client.post(
        "/feedback/task-weight",
        json={
            "job_id": outcome_id,
            "task_name": "Already Max",
            "direction": "boost",
            "reason": "Keep important",
        },
    )
    assert task_feedback_resp.status_code == 200
    data = task_feedback_resp.json()
    assert data["new_weights"]["Already Max"] == 1.0
    assert "maximum" in " ".join(data["changes"])
