from app.models.feedback import Feedback
from app.models.job import Job
from app.models.outcome import Outcome


def test_analytics_metrics_count_jobs_not_outcomes(client, db_session):
    active_job = Job(
        id="analytics-job-active",
        title="AI Engineer Intern",
        description="Build AI systems",
        company="SignalStack",
        location="Remote",
        status="active",
    )
    second_active_job = Job(
        id="analytics-job-active-empty",
        title="Backend Engineer Intern",
        description="Build APIs",
        company="SignalStack",
        location="Remote",
        status="active",
    )
    archived_job = Job(
        id="analytics-job-archived",
        title="Archived Role",
        description="Old role",
        company="SignalStack",
        location="Remote",
        status="archived",
    )
    outcomes = [
        Outcome(id="analytics-outcome-1", job_id=active_job.id, title="Outcome 1", description="One"),
        Outcome(id="analytics-outcome-2", job_id=active_job.id, title="Outcome 2", description="Two"),
        Outcome(id="analytics-outcome-3", job_id=active_job.id, title="Outcome 3", description="Three"),
        Outcome(id="analytics-outcome-archived", job_id=archived_job.id, title="Archived", description="Old"),
    ]
    db_session.add_all([active_job, second_active_job, archived_job, *outcomes])
    db_session.flush()
    db_session.add_all([
        Feedback(
            job_id="analytics-outcome-1",
            result="success",
            metrics_json={
                "action_taken": "hire",
                "selected_candidates": ["alice@example.com", "bob@example.com"],
                "rejected_candidates": ["cara@example.com"],
            },
        ),
        Feedback(
            job_id="analytics-outcome-2",
            result="failure",
            metrics_json={
                "action_taken": "reject",
                "rejected_candidates": ["dan@example.com"],
            },
        ),
    ])
    db_session.commit()

    response = client.get("/analytics/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_active_jobs"] == 2
    assert payload["total_candidates_processed"] == 4
    assert payload["total_hired"] == 2
    assert payload["total_rejected"] == 2
    assert payload["acceptance_rate"] == 50.0


def test_analytics_decisions_include_details_path(client, db_session):
    job = Job(
        id="analytics-history-job",
        title="AI Engineer Intern",
        description="Build AI systems",
        company="SignalStack",
        location="Remote",
        status="active",
    )
    outcome = Outcome(
        id="analytics-history-outcome",
        job_id=job.id,
        title="Productionize AI Backend Services",
        description="Turn prototypes into APIs",
        company="SignalStack",
    )
    feedback = Feedback(
        job_id=outcome.id,
        result="success",
        metrics_json={
            "action_taken": "hire",
            "selected_candidate": "alice@example.com",
        },
    )
    db_session.add_all([job, outcome, feedback])
    db_session.commit()

    response = client.get("/analytics/decisions")

    assert response.status_code == 200
    payload = response.json()
    row = next(item for item in payload if item["id"] == feedback.id)
    assert row["job_title"] == "Productionize AI Backend Services"
    assert row["candidate"] == "alice@example.com"
    assert row["decision"] == "Hired"
    assert row["details_path"] == "/evaluation/analytics-history-outcome"
