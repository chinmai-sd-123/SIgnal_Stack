import pytest


@pytest.mark.integration
def test_create_and_get_outcome(client):
    payload = {
        "title": "Backend API Platform",
        "description": "Build a backend API with auth",
        "company": "SignalStack",
        "location": "Remote",
        "category": "Software Engineering",
        "job_type": "Full-time",
        "tasks": [
            {"name": "Implement Auth", "priority": "High", "weight": 0.6},
            {"name": "Add Tests", "priority": "Medium", "weight": 0.4},
        ],
    }

    response = client.post("/outcomes", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["id"]
    assert data["title"] == payload["title"]
    assert data["public_url"].startswith("http://test.local/")

    get_response = client.get(f"/outcomes/{data['id']}")
    assert get_response.status_code == 200
    get_data = get_response.json()
    assert get_data["id"] == data["id"]


@pytest.mark.integration
def test_create_tasks_batch(client):
    outcome_payload = {
        "title": "Data Pipeline",
        "description": "Build ingestion pipeline",
        "company": "SignalStack",
        "location": "Remote",
        "category": "Data Engineering",
        "job_type": "Full-time",
        "tasks": [],
    }
    outcome_resp = client.post("/outcomes", json=outcome_payload)
    assert outcome_resp.status_code == 200
    outcome_id = outcome_resp.json()["id"]

    batch_payload = {
        "outcome_id": outcome_id,
        "tasks": [
            {"name": "Design Schema", "priority": "High", "weight": 0},
            {"name": "Build ETL", "priority": "High", "weight": 0},
            {"name": "Add Monitoring", "priority": "Low", "weight": 0},
        ],
    }
    batch_resp = client.post("/tasks/batch", json=batch_payload)
    assert batch_resp.status_code == 200
    data = batch_resp.json()
    assert len(data) == 3
    weights = [t["weight"] for t in data]
    assert sum(weights) == pytest.approx(1.0, rel=1e-3)


@pytest.mark.integration
def test_submit_and_get_proofs(client):
    outcome_payload = {
        "title": "Frontend UI",
        "description": "Build UI",
        "company": "SignalStack",
        "location": "Remote",
        "category": "Frontend",
        "job_type": "Contract",
        "tasks": [],
    }
    outcome_resp = client.post("/outcomes", json=outcome_payload)
    outcome_id = outcome_resp.json()["id"]

    proof_payload = {
        "job_id": outcome_id,
        "candidate_id": "cand-1",
        "type": "artifact",
        "payload": {"artifact_link": "https://example.com/artifact"},
    }
    proof_resp = client.post("/proofs", json=proof_payload)
    assert proof_resp.status_code == 200

    get_resp = client.get(f"/proofs/{outcome_id}")
    assert get_resp.status_code == 200
    proofs = get_resp.json()
    assert len(proofs) == 1
    assert proofs[0]["candidate_id"] == "cand-1"
