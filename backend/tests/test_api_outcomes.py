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


@pytest.mark.integration
def test_invited_candidate_is_backfilled_to_outcome_created_after_submission(client):
    job_resp = client.post("/jobs", json={
        "title": "Machine Learning Engineer Intern",
        "description": "Evaluate intern ML projects",
        "company": "SignalStack",
        "location": "Remote",
        "category": "Machine Learning",
        "job_type": "Internship",
        "required_languages": ["Python"],
    })
    assert job_resp.status_code == 200
    job_id = job_resp.json()["id"]

    invite_resp = client.post(f"/jobs/{job_id}/invites")
    assert invite_resp.status_code == 200
    token = invite_resp.json()["token"]

    submit_resp = client.post(f"/invites/{token}/submit", json={
        "candidate_name": "Candidate One",
        "candidate_email": "candidate@example.com",
        "github_username": "candidate-one",
        "repo_url": "https://github.com/candidate-one/health-monitor",
        "resume_url": "https://drive.google.com/resume",
    })
    assert submit_resp.status_code == 200

    outcome_resp = client.post("/outcomes", json={
        "job_id": job_id,
        "title": "Train Health Monitoring Model",
        "description": "Train a baseline ML model for health risk prediction",
        "company": "SignalStack",
        "location": "Remote",
        "category": "Machine Learning",
        "job_type": "Internship",
        "tasks": [
            {"name": "Train baseline model", "priority": "High", "weight": 1.0},
        ],
    })
    assert outcome_resp.status_code == 200
    outcome_id = outcome_resp.json()["id"]

    proofs_resp = client.get(f"/proofs/{outcome_id}")
    assert proofs_resp.status_code == 200
    proofs = proofs_resp.json()

    assert len(proofs) == 1
    assert proofs[0]["candidate_id"] == "candidate-one"
    assert proofs[0]["payload"]["repo_url"] == "https://github.com/candidate-one/health-monitor"
    assert proofs[0]["payload"]["resume_url"] == "https://drive.google.com/resume"
    assert proofs[0]["payload"]["artifact_link"] == ""


@pytest.mark.integration
def test_candidate_invite_page_loads_job_outcomes(client):
    job_resp = client.post("/jobs", json={
        "title": "AI Software Engineer Intern",
        "description": "Build AI developer tools",
        "company": "SignalStack",
        "location": "Remote",
        "category": "Software Engineering",
        "job_type": "Internship",
    })
    assert job_resp.status_code == 200
    job_id = job_resp.json()["id"]

    outcome_resp = client.post("/outcomes", json={
        "job_id": job_id,
        "title": "Build AI Code Review Workflow",
        "description": "Submit code to an LLM and return structured review feedback",
        "company": "SignalStack",
        "location": "Remote",
        "category": "Software Engineering",
        "job_type": "Internship",
        "tasks": [
            {"name": "Implement review API integration", "priority": "High", "weight": 1.0},
        ],
    })
    assert outcome_resp.status_code == 200

    invite_resp = client.post(f"/jobs/{job_id}/invites")
    assert invite_resp.status_code == 200
    token = invite_resp.json()["token"]

    get_resp = client.get(f"/invites/{token}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["token"] == token
    assert data["job"]["id"] == job_id
    assert data["job"]["outcomes"] == [
        {
            "id": outcome_resp.json()["id"],
            "title": "Build AI Code Review Workflow",
            "description": "Submit code to an LLM and return structured review feedback",
        }
    ]


@pytest.mark.integration
def test_save_as_template_uses_nullable_template_job_id(client):
    job_resp = client.post("/jobs", json={
        "title": "AI Engineer Intern",
        "description": "Build applied AI systems",
        "company": "SignalStack",
        "location": "Remote",
        "category": "Software Engineering",
        "job_type": "Internship",
    })
    assert job_resp.status_code == 200
    job_id = job_resp.json()["id"]

    outcome_resp = client.post("/outcomes", json={
        "job_id": job_id,
        "title": "Ship AI Backend Services",
        "description": "Turn AI prototypes into reliable backend APIs",
        "company": "SignalStack",
        "location": "Remote",
        "category": "Software Engineering",
        "job_type": "Internship",
        "save_as_template": True,
        "tasks": [
            {"name": "Expose an AI workflow through an API", "priority": "High", "weight": 1.0},
        ],
    })
    assert outcome_resp.status_code == 200
    instance = outcome_resp.json()
    assert instance["job_id"] == job_id
    assert instance["is_template"] == 0
    assert instance["source_template_id"]

    templates_resp = client.get("/outcomes/templates")
    assert templates_resp.status_code == 200
    templates = templates_resp.json()
    master = next(template for template in templates if template["id"] == instance["source_template_id"])
    assert master["job_id"] is None
    assert master["is_template"] == 1
    assert master["title"] == "Ship AI Backend Services"
