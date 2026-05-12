from datetime import timedelta

from app.models.evaluation import Evaluation
from app.models.invite import Invite, InviteSubmission
from app.models.job import Job
from app.models.job_candidate import JobCandidate
from app.models.outcome import Outcome
from app.models.proof import Proof
from app.utils.time_utils import utc_now


def test_queue_endpoint_refreshes_stale_one_candidate_report(client, db_session, monkeypatch):
    from app.routes import job as job_routes

    job_id = "queue-refresh-job"
    outcome_id = "queue-refresh-outcome"
    job = Job(
        id=job_id,
        title="AI Engineer Intern",
        description="Evaluate reports",
        company="SignalStack",
        location="Remote",
        status="active",
    )
    outcome = Outcome(
        id=outcome_id,
        job_id=job_id,
        title="Productionize AI Backend Services",
        description="Turn prototypes into APIs",
    )
    invite = Invite(
        id="queue-refresh-invite",
        token="queue-refresh-token",
        job_id=job_id,
        status="active",
        expires_at=utc_now() + timedelta(days=7),
    )
    submissions = [
        InviteSubmission(
            id="queue-refresh-sub-1",
            invite_id=invite.id,
            job_id=job_id,
            candidate_name="Johny",
            candidate_email="john@example.com",
            github_username="chinmai-sd-123",
            repo_url="https://github.com/chinmai-sd-123/AI_coach",
            status="evaluated",
        ),
        InviteSubmission(
            id="queue-refresh-sub-2",
            invite_id=invite.id,
            job_id=job_id,
            candidate_name="Chinmai",
            candidate_email="power@example.com",
            github_username="chinmai-sd-123",
            repo_url="https://github.com/chinmai-sd-123/SIgnal_Stack",
            status="evaluated",
        ),
    ]
    candidates = [
        JobCandidate(
            id="queue-refresh-candidate-1",
            job_id=job_id,
            candidate_id="john@example.com",
            status="evaluated",
            evaluation_score=51,
            evaluation_data={"submission": {"candidate_name": "Johny"}},
        ),
        JobCandidate(
            id="queue-refresh-candidate-2",
            job_id=job_id,
            candidate_id="power@example.com",
            status="evaluated",
            evaluation_score=62,
            evaluation_data={"submission": {"candidate_name": "Chinmai"}},
        ),
    ]
    proofs = [
        Proof(
            outcome_id=outcome_id,
            candidate_id="john@example.com",
            type="github",
            payload_json={"source": "invite", "invite_submission_id": submissions[0].id},
        ),
        Proof(
            outcome_id=outcome_id,
            candidate_id="power@example.com",
            type="github",
            payload_json={"source": "invite", "invite_submission_id": submissions[1].id},
        ),
    ]
    db_session.add_all([job, outcome, invite])
    db_session.flush()
    db_session.add_all([*submissions, *candidates, *proofs])
    db_session.flush()
    stale_report = Evaluation(
        job_id=outcome_id,
        outcome_id=outcome_id,
        status="completed",
        fit_score=55,
        evaluation_json={
            "candidate_summaries": [
                {"candidate_id": "john@example.com", "overall_score": 0.55},
            ],
        },
    )
    db_session.add(stale_report)
    db_session.commit()

    original_progress = job_routes.get_job_evaluation_progress

    def active_progress(db, requested_job_id):
        progress = original_progress(db, requested_job_id)
        progress["queue_active"] = True
        progress["queue_size"] = 1
        return progress

    monkeypatch.setattr(job_routes, "get_job_evaluation_progress", active_progress)
    monkeypatch.setattr(job_routes, "queue_job_evaluation", lambda *args, **kwargs: "followup-task")

    response = client.post(
        f"/jobs/{job_id}/evaluations/queue",
        json={"include_deep_evaluation": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == "followup-task"
    assert payload["message"] == "Evaluation follow-up queued to refresh reports"
