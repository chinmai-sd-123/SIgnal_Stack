import pytest


@pytest.mark.integration
def test_update_and_delete_outcome(client):
    create_payload = {
        "title": "Initial Outcome",
        "description": "Initial description",
        "company": "SignalStack",
        "location": "Remote",
        "category": "Software Engineering",
        "proof_type": "github",
        "tasks": [
            {"name": "Initial signal", "priority": "High", "weight": 1.0},
        ],
    }
    created = client.post("/outcomes", json=create_payload)
    assert created.status_code == 200
    outcome_id = created.json()["id"]

    update_payload = {
        "title": "Updated Outcome",
        "description": "Updated success criteria",
        "proof_type": "mixed",
        "tasks": [
            {"name": "Updated high signal", "priority": "High", "weight": 0.5},
            {"name": "Updated medium signal", "priority": "Medium", "weight": 0.5},
        ],
    }
    updated = client.patch(f"/outcomes/{outcome_id}", json=update_payload)
    assert updated.status_code == 200
    updated_body = updated.json()
    assert updated_body["title"] == "Updated Outcome"
    assert updated_body["proof_type"] == "mixed"
    assert [task["name"] for task in updated_body["tasks"]] == [
        "Updated high signal",
        "Updated medium signal",
    ]

    deleted = client.delete(f"/outcomes/{outcome_id}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"

    missing = client.get(f"/outcomes/{outcome_id}")
    assert missing.status_code == 404
