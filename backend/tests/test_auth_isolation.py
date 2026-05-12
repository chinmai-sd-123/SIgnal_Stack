from fastapi.testclient import TestClient


def _admin_headers(db_session):
    from app.models.recruiter import Recruiter
    from app.services.auth import create_access_token, hash_password

    admin = Recruiter(
        id="auth-test-admin",
        email="admin@signalstack.dev",
        password=hash_password("Password@123"),
        role="admin",
        name="Admin",
    )
    db_session.merge(admin)
    db_session.flush()
    return {"Authorization": f"Bearer {create_access_token(admin)}"}


def _login(client: TestClient, email: str, password: str = "Password@123") -> tuple[dict, dict]:
    response = client.post("/recruiter/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    payload = response.json()
    return {"Authorization": f"Bearer {payload['access_token']}"}, payload["recruiter"]


def _invite_and_signup(client: TestClient, admin_headers: dict, email: str) -> tuple[dict, dict]:
    invite_response = client.post("/recruiter/invites", headers=admin_headers, json={"email": email})
    assert invite_response.status_code == 200, invite_response.text
    invite = invite_response.json()
    signup_response = client.post(
        "/recruiter/signup",
        json={
            "email": email,
            "password": "Password@123",
            "invite_token": invite["token"],
        },
    )
    assert signup_response.status_code == 200, signup_response.text
    payload = signup_response.json()
    return {"Authorization": f"Bearer {payload['access_token']}"}, payload["recruiter"]


def test_recruiters_only_see_their_own_jobs(app_with_overrides, db_session):
    app, db, _, _ = app_with_overrides

    def _get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[db.get_db] = _get_db
    try:
        with TestClient(app) as client:
            unknown_login = client.post(
                "/recruiter/login",
                json={"email": "unknown-recruiter@signalstack.dev", "password": "Password@123"},
            )
            assert unknown_login.status_code == 401

            admin_headers = _admin_headers(db_session)
            recruiter_a_headers, recruiter_a = _invite_and_signup(
                client,
                admin_headers,
                "alpha-recruiter@signalstack.dev",
            )
            recruiter_b_headers, recruiter_b = _invite_and_signup(
                client,
                admin_headers,
                "beta-recruiter@signalstack.dev",
            )

            job_a = client.post(
                "/jobs",
                headers=recruiter_a_headers,
                json={
                    "title": "AI Engineer Intern",
                    "description": "Build applied AI systems.",
                    "company": "Alpha",
                    "location": "Remote",
                    "category": "Software Engineering",
                },
            )
            assert job_a.status_code == 200, job_a.text

            job_b = client.post(
                "/jobs",
                headers=recruiter_b_headers,
                json={
                    "title": "Backend Engineer Intern",
                    "description": "Build reliable APIs.",
                    "company": "Beta",
                    "location": "Remote",
                    "category": "Software Engineering",
                },
            )
            assert job_b.status_code == 200, job_b.text

            job_a_payload = job_a.json()
            job_b_payload = job_b.json()
            assert job_a_payload["recruiter_id"] == recruiter_a["id"]
            assert job_b_payload["recruiter_id"] == recruiter_b["id"]

            recruiter_a_jobs = client.get("/jobs?include_archived=true", headers=recruiter_a_headers)
            assert recruiter_a_jobs.status_code == 200
            assert {job["id"] for job in recruiter_a_jobs.json()} == {job_a_payload["id"]}

            blocked = client.get(f"/jobs/{job_b_payload['id']}", headers=recruiter_a_headers)
            assert blocked.status_code == 404

            admin_only = client.get("/admin/signal-weights", headers=recruiter_a_headers)
            assert admin_only.status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_hard_delete_job_requires_confirmation_and_removes_linked_data(app_with_overrides, db_session):
    app, db, _, _ = app_with_overrides

    def _get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[db.get_db] = _get_db
    try:
        with TestClient(app) as client:
            from app.models.audit import AuditLog
            from app.models.evaluation import Evaluation
            from app.models.feedback import Feedback, SignalWeight
            from app.models.invite import Invite, InviteSubmission
            from app.models.job import Job
            from app.models.job_candidate import JobCandidate
            from app.models.outcome import Outcome
            from app.models.proof import Proof
            from app.models.snapshot import LLMLog
            from app.models.task import Task, TaskWeightHistory
            from app.utils.time_utils import utc_now

            admin_headers = _admin_headers(db_session)
            job = Job(
                id="delete-job-1",
                recruiter_id="auth-test-admin",
                title="Delete Me",
                description="Temporary role",
                company="SignalStack",
                location="Remote",
                status="active",
            )
            outcome = Outcome(
                id="delete-outcome-1",
                job_id=job.id,
                title="Outcome",
                description="Outcome description",
            )
            task = Task(
                id="delete-task-1",
                outcome_id=outcome.id,
                name="Task",
                priority="High",
                weight=1.0,
                version=1,
            )
            invite = Invite(
                id="delete-invite-1",
                token="delete-token-1",
                job_id=job.id,
                status="active",
                expires_at=utc_now(),
            )
            submission = InviteSubmission(
                id="delete-submission-1",
                invite_id=invite.id,
                job_id=job.id,
                candidate_name="Candidate",
                candidate_email="candidate@example.com",
                github_username="candidate",
                repo_url="https://github.com/acme/candidate",
                status="evaluated",
            )
            candidate = JobCandidate(
                id="delete-candidate-1",
                job_id=job.id,
                candidate_id="candidate@example.com",
                status="evaluated",
                evaluation_score=75,
            )
            proof = Proof(
                outcome_id=outcome.id,
                candidate_id="candidate@example.com",
                type="github",
                payload_json={"source": "invite", "invite_submission_id": submission.id},
            )
            evaluation = Evaluation(
                job_id=outcome.id,
                outcome_id=outcome.id,
                status="completed",
                fit_score=0.75,
                evaluation_json={"candidate_summaries": [{"candidate_id": "candidate@example.com"}]},
            )
            signal_weight = SignalWeight(signal_name="delete_signal", task_id=task.id, weight=1.0)
            task_history = TaskWeightHistory(
                task_id=task.id,
                outcome_id=outcome.id,
                old_weight=0.5,
                new_weight=1.0,
                reason="test",
                feedback_source_job_id=job.id,
            )
            audit_job = AuditLog(entity_type="job", entity_id=job.id, action="created", details_json={})
            audit_outcome = AuditLog(entity_type="outcome", entity_id=outcome.id, action="created", details_json={})
            db_session.add_all([job, outcome])
            db_session.flush()
            db_session.add_all([
                task,
                invite,
                submission,
                candidate,
                proof,
                evaluation,
                signal_weight,
                task_history,
                audit_job,
                audit_outcome,
            ])
            db_session.flush()
            db_session.add_all([
                Feedback(evaluation_id=evaluation.id, job_id=job.id, result="success", metrics_json={}),
                LLMLog(evaluation_id=evaluation.id, prompt="prompt", raw_response="{}", is_valid=1),
            ])
            db_session.commit()
            job_id = job.id
            outcome_id = outcome.id
            task_id = task.id
            evaluation_id = evaluation.id

            rejected = client.delete(
                f"/jobs/{job_id}?hard_delete=true&confirmation=WRONG",
                headers=admin_headers,
            )
            assert rejected.status_code == 400
            assert db_session.query(Job).filter(Job.id == job_id).count() == 1

            deleted = client.delete(
                f"/jobs/{job_id}?hard_delete=true&confirmation=DELETE",
                headers=admin_headers,
            )
            assert deleted.status_code == 200, deleted.text
            assert deleted.json()["type"] == "hard_delete"

            for model, column, value in [
                (Job, Job.id, job_id),
                (Outcome, Outcome.job_id, job_id),
                (Task, Task.outcome_id, outcome_id),
                (Invite, Invite.job_id, job_id),
                (InviteSubmission, InviteSubmission.job_id, job_id),
                (JobCandidate, JobCandidate.job_id, job_id),
                (Proof, Proof.outcome_id, outcome_id),
                (Evaluation, Evaluation.outcome_id, outcome_id),
                (Feedback, Feedback.job_id, job_id),
                (SignalWeight, SignalWeight.task_id, task_id),
                (TaskWeightHistory, TaskWeightHistory.feedback_source_job_id, job_id),
                (AuditLog, AuditLog.entity_id, job_id),
                (AuditLog, AuditLog.entity_id, outcome_id),
            ]:
                assert db_session.query(model).filter(column == value).count() == 0

            assert db_session.query(LLMLog).filter(LLMLog.evaluation_id == evaluation_id).count() == 0
    finally:
        app.dependency_overrides.clear()
