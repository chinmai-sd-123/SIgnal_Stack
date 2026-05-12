import pytest
from datetime import timedelta

import app.schemas as schemas
from app.models.evaluation import Evaluation
from app.models.invite import InviteSubmission
from app.models.invite import Invite
from app.models.job import Job
from app.models.job_candidate import JobCandidate
from app.models.outcome import Outcome
from app.models.proof import Proof
from app.models.task import Task
from app.services import bulk_evaluation_service as bulk
from app.utils.time_utils import utc_now


class _FakeCandidateQuery:
    def __init__(self, candidate):
        self.candidate = candidate

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.candidate


class _FakeCandidateDb:
    def __init__(self, candidate):
        self.candidate = candidate

    def query(self, model):
        return _FakeCandidateQuery(self.candidate)


class _FakeProofQuery:
    def __init__(self, proofs):
        self.proofs = proofs

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self.proofs


class _FakeProofDb:
    def __init__(self, proofs):
        self.proofs = proofs

    def query(self, model):
        return _FakeProofQuery(self.proofs)


class _FakeRecoveryQuery:
    def __init__(self, rows):
        self.rows = rows

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self.rows


class _FakeRecoveryDb:
    def __init__(self, submissions, candidates):
        self.submissions = submissions
        self.candidates = candidates
        self.commits = 0

    def query(self, model):
        if model is InviteSubmission:
            return _FakeRecoveryQuery(self.submissions)
        if model is JobCandidate:
            return _FakeRecoveryQuery(self.candidates)
        return _FakeRecoveryQuery([])

    def commit(self):
        self.commits += 1


class _FakeSubmissionQuery:
    def __init__(self, rows):
        self.rows = rows
        self.statuses = None

    def filter(self, *criteria):
        for criterion in criteria:
            right = getattr(criterion, "right", None)
            value = getattr(right, "value", None)
            if isinstance(value, list):
                self.statuses = set(value)
        return self

    def all(self):
        if self.statuses is None:
            return self.rows
        return [row for row in self.rows if row.status in self.statuses]


class _FakeSubmissionQueueDb:
    def __init__(self, submissions, candidates):
        self.submissions = submissions
        self.candidates = candidates
        self.commits = 0

    def query(self, model):
        if model is InviteSubmission:
            return _FakeSubmissionQuery(self.submissions)
        if model is JobCandidate:
            return _FakeCandidateQuery(None)
        return _FakeRecoveryQuery([])

    def add(self, candidate):
        self.candidates.append(candidate)

    def commit(self):
        self.commits += 1


class _FakeEvaluatedCandidateQuery:
    def __init__(self, candidates):
        self.candidates = candidates
        self.limit_value = None

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        self.candidates.sort(key=lambda candidate: candidate.evaluation_score or 0, reverse=True)
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def all(self):
        if self.limit_value is None:
            return self.candidates
        return self.candidates[:self.limit_value]


class _FakeEvaluatedCandidateDb:
    def __init__(self, candidates):
        self.candidates = candidates

    def query(self, model):
        if model is JobCandidate:
            return _FakeEvaluatedCandidateQuery(self.candidates)
        return _FakeRecoveryQuery([])


class _Proof:
    def __init__(self, invite_submission_id, outcome_id="outcome-1"):
        self.outcome_id = outcome_id
        self.payload_json = {"invite_submission_id": invite_submission_id}


class _FakeRedis:
    def __init__(self):
        self.items = []
        self.values = {}
        self.lists = {}

    def lpush(self, key, value):
        self.items.append((key, value))
        self.lists.setdefault(key, []).insert(0, value)

    def setex(self, key, ttl, value):
        self.values[key] = (ttl, value)

    def llen(self, key):
        return len(self.lists.get(key, []))

    def lrange(self, key, start, end):
        items = self.lists.get(key, [])
        if end == -1:
            return items[start:]
        return items[start:end + 1]

    def lrem(self, key, count, value):
        items = self.lists.get(key, [])
        removed = 0
        remaining = []
        limit = abs(count)
        for item in items:
            should_remove = item == value and (count == 0 or removed < limit)
            if should_remove:
                removed += 1
            else:
                remaining.append(item)
        self.lists[key] = remaining
        return removed


class _NoCloseSession:
    def __init__(self, session):
        self.session = session

    def __getattr__(self, name):
        return getattr(self.session, name)

    def close(self):
        pass


class _FakeExtractor:
    def extract_signals(self, proof):
        return {
            "authorship_fraction": 1.0,
            "readme_quality_score": 1.0,
            "tests_present": 1.0,
            "commit_count": 3,
            "repo_url": proof.payload.get("repo_url", ""),
        }


class _FakeEvaluator:
    def evaluate(self, outcome, proofs, signals_map):
        summaries = []
        for index, proof in enumerate(proofs):
            score = round(max(0.1, 0.9 - index * 0.05), 2)
            summaries.append(schemas.CandidateSummary(
                candidate_id=proof.candidate_id,
                overall_score=score,
                capability_score=score,
                evidence_confidence=0.8,
                production_readiness=0.7,
                verification_status="verified",
                tasks_won=1 if index == 0 else 0,
                dimensions={
                    "project_completion": score,
                    "engineering_quality": score,
                    "communication": 0.7,
                    "innovation": 0.6,
                    "depth_novelty": 0.6,
                },
                confidence_rating="High",
                risk_flags=[],
            ))

        top_candidates = [
            schemas.CandidateScore(
                candidate_id=summary.candidate_id,
                score=summary.overall_score,
                justification="Test evaluator score",
                evidence=[],
            )
            for summary in summaries
        ]
        return schemas.EvaluationResponse(
            job_id=outcome.id,
            job_title=outcome.title,
            fit_score=summaries[0].overall_score if summaries else 0.0,
            capability_score=summaries[0].capability_score if summaries else 0.0,
            evidence_confidence=0.8 if summaries else 0.0,
            production_readiness=0.7 if summaries else 0.0,
            verification_status="verified" if summaries else "unverified",
            work_allocation=[
                schemas.WorkAllocation(
                    task_id=outcome.tasks[0].id,
                    task_title=outcome.tasks[0].name,
                    recommended_candidate=summaries[0].candidate_id if summaries else "None",
                    confidence=summaries[0].overall_score if summaries else 0.0,
                    reasons=["Test allocation"],
                    evidence=[],
                    top_candidates=top_candidates,
                )
            ],
            global_signals_used=["readme_quality_score", "tests_present"],
            risk_flags=[],
            human_action_required=True,
            dimensions=summaries[0].dimensions if summaries else None,
            candidate_summaries=summaries,
        )


def _add_submission_with_proofs(db, invite, job_id, outcomes, candidate_id, status="submitted"):
    email = f"{candidate_id}@example.com"
    submission = InviteSubmission(
        id=f"sub-{candidate_id}",
        invite_id=invite.id,
        job_id=job_id,
        candidate_name=candidate_id.title(),
        candidate_email=email,
        github_username=candidate_id,
        repo_url=f"https://github.com/acme/{candidate_id}",
        status=status,
    )
    db.add(submission)
    for outcome in outcomes:
        db.add(Proof(
            outcome_id=outcome.id,
            candidate_id=email,
            type="github",
            payload_json={
                "repo_url": submission.repo_url,
                "github_username": candidate_id,
                "candidate_email": email,
                "invite_submission_id": submission.id,
            },
        ))
    db.commit()
    return submission


@pytest.mark.unit
def test_ensure_job_candidate_moves_queued_candidate_to_evaluating():
    candidate = JobCandidate(
        id="jc-1",
        job_id="job-1",
        candidate_id="candidate-1",
        status="queued",
    )

    result = bulk.ensure_job_candidate(
        _FakeCandidateDb(candidate),
        "job-1",
        "candidate-1",
        status="evaluating",
    )

    assert result.status == "evaluating"


@pytest.mark.unit
def test_find_submission_proof_prefers_exact_invite_submission(monkeypatch):
    monkeypatch.setattr(bulk, "_job_outcome_ids", lambda db, job_id: ["outcome-1"])
    submission = InviteSubmission(id="sub-current", job_id="job-1")
    stale_proof = _Proof("sub-old")
    current_proof = _Proof("sub-current")

    proof = bulk._find_submission_proof(
        _FakeProofDb([stale_proof, current_proof]),
        submission,
        "candidate-1",
    )

    assert proof is current_proof


@pytest.mark.unit
def test_queue_job_evaluation_uses_redis_when_available(monkeypatch):
    fake_redis = _FakeRedis()
    monkeypatch.setattr(bulk.cache, "redis_client", fake_redis)
    monkeypatch.setattr(bulk, "init_redis_job_evaluation_worker", lambda: True)

    task_id = bulk.queue_job_evaluation(
        "job-1",
        deep_limit=7,
        candidate_limit=20,
        include_deep_evaluation=False,
    )

    assert task_id
    assert fake_redis.items[0][0] == bulk.REDIS_JOB_EVAL_QUEUE
    assert f"{bulk.REDIS_JOB_EVAL_TASK_PREFIX}:{task_id}" in fake_redis.values


@pytest.mark.unit
def test_job_evaluation_queue_size_is_scoped_to_job(monkeypatch):
    fake_redis = _FakeRedis()
    monkeypatch.setattr(bulk.cache, "redis_client", fake_redis)

    fake_redis.lpush(bulk.REDIS_JOB_EVAL_QUEUE, '{"task_id":"task-1","job_id":"job-1"}')
    fake_redis.lpush(bulk.REDIS_JOB_EVAL_QUEUE, '{"task_id":"task-2","job_id":"job-2"}')
    fake_redis.lpush(bulk.REDIS_JOB_EVAL_PROCESSING, '{"task_id":"task-3","job_id":"job-1"}')

    assert bulk.get_job_evaluation_queue_size("job-1") == 2
    assert bulk.get_job_evaluation_queue_size("job-2") == 1
    assert bulk.get_job_evaluation_queue_size("missing-job") == 0
    assert bulk.get_job_evaluation_queue_size() == 3


@pytest.mark.unit
def test_pending_redis_job_queue_wakes_worker(monkeypatch):
    fake_redis = _FakeRedis()
    monkeypatch.setattr(bulk.cache, "redis_client", fake_redis)
    starts = []
    monkeypatch.setattr(bulk, "init_redis_job_evaluation_worker", lambda: starts.append(True) or True)

    assert bulk.ensure_redis_job_evaluation_worker_for_pending("missing-job") is False
    assert starts == []

    fake_redis.lpush(bulk.REDIS_JOB_EVAL_QUEUE, '{"task_id":"task-1","job_id":"job-1"}')

    assert bulk.ensure_redis_job_evaluation_worker_for_pending("job-1") is True
    assert starts == [True]


@pytest.mark.unit
def test_completed_job_progress_clears_stale_redis_queue(monkeypatch):
    fake_redis = _FakeRedis()
    monkeypatch.setattr(bulk.cache, "redis_client", fake_redis)

    fake_redis.lpush(bulk.REDIS_JOB_EVAL_QUEUE, '{"task_id":"task-complete","job_id":"job-1"}')
    fake_redis.lpush(bulk.REDIS_JOB_EVAL_PROCESSING, '{"task_id":"task-other","job_id":"job-2"}')

    complete_progress = {
        "submissions_total": 2,
        "evaluated_count": 2,
        "outcomes_total": 1,
        "outcomes_evaluated": 1,
        "active_count": 0,
        "submission_status_counts": {"evaluated": 2},
        "candidate_status_counts": {"evaluated": 2},
    }

    assert bulk.progress_indicates_complete(complete_progress) is True
    assert bulk.clear_job_evaluation_queue("job-1", reason="test_complete") == 1
    assert bulk.get_job_evaluation_queue_size("job-1") == 0
    assert bulk.get_job_evaluation_queue_size("job-2") == 1
    assert any("task-complete" in value for _, value in fake_redis.values.values())


@pytest.mark.unit
def test_progress_not_complete_when_report_missing_or_candidates_active():
    assert bulk.progress_indicates_complete({
        "submissions_total": 2,
        "evaluated_count": 2,
        "outcomes_total": 1,
        "outcomes_evaluated": 0,
        "active_count": 0,
        "submission_status_counts": {"evaluated": 2},
        "candidate_status_counts": {"evaluated": 2},
    }) is False

    assert bulk.progress_indicates_complete({
        "submissions_total": 2,
        "evaluated_count": 2,
        "outcomes_total": 1,
        "outcomes_evaluated": 1,
        "active_count": 1,
        "submission_status_counts": {"evaluated": 1, "queued": 1},
        "candidate_status_counts": {"evaluated": 1, "queued": 1},
    }) is False


@pytest.mark.unit
def test_queued_only_progress_can_be_reenqueued():
    progress = {
        "queue_active": False,
        "submission_status_counts": {"queued": 1},
        "candidate_status_counts": {"queued": 1},
    }

    assert bulk.has_running_job_evaluation(progress) is False


@pytest.mark.unit
def test_evaluating_or_worker_progress_is_running():
    assert bulk.has_running_job_evaluation({
        "queue_active": False,
        "submission_status_counts": {"evaluating": 1},
        "candidate_status_counts": {},
    }) is True
    assert bulk.has_running_job_evaluation({
        "queue_active": True,
        "submission_status_counts": {"queued": 1},
        "candidate_status_counts": {"queued": 1},
    }) is True


@pytest.mark.unit
def test_recover_interrupted_evaluations_requeues_stuck_rows():
    submission = InviteSubmission(id="sub-1", job_id="job-1", status="evaluating")
    candidate = JobCandidate(
        id="cand-1",
        job_id="job-1",
        candidate_id="candidate-1",
        status="evaluating",
        evaluation_score=None,
        evaluation_data={"stage": "evaluating"},
    )
    db = _FakeRecoveryDb([submission], [candidate])

    recovered = bulk._recover_interrupted_evaluations(db, "job-1")

    assert recovered == 1
    assert submission.status == "queued"
    assert candidate.status == "queued"
    assert candidate.evaluation_data["stage"] == "queued"
    assert db.commits == 1


@pytest.mark.unit
def test_mark_job_submissions_queued_can_retry_failed_only():
    submitted = InviteSubmission(id="sub-new", job_id="job-1", status="submitted", github_username="new")
    failed = InviteSubmission(id="sub-failed", job_id="job-1", status="failed", github_username="failed")
    evaluated = InviteSubmission(id="sub-done", job_id="job-1", status="evaluated", github_username="done")
    db = _FakeSubmissionQueueDb([submitted, failed, evaluated], [])

    queued = bulk.mark_job_submissions_queued(db, "job-1", retry_failed_only=True)

    assert queued == 1
    assert submitted.status == "submitted"
    assert failed.status == "queued"
    assert evaluated.status == "evaluated"
    assert db.candidates[0].candidate_id == "failed"


@pytest.mark.unit
def test_deep_evaluation_plan_includes_all_previously_evaluated_candidates():
    old_candidate = JobCandidate(
        id="jc-old",
        job_id="job-1",
        candidate_id="old",
        evaluation_score=90,
        evaluation_data={"signals": {"tests_present": 1}},
    )
    new_candidate = JobCandidate(
        id="jc-new",
        job_id="job-1",
        candidate_id="new",
        evaluation_score=80,
        evaluation_data={"signals": {"readme_quality_score": 1}},
    )
    signals = {"new": {"commit_count": 1}}

    candidate_ids = bulk._candidate_ids_for_deep_evaluation(
        _FakeEvaluatedCandidateDb([new_candidate, old_candidate]),
        "job-1",
        100,
        signals,
    )

    assert candidate_ids == ["old", "new"]
    assert signals["old"] == {"tests_present": 1}
    assert signals["new"] == {"commit_count": 1}


@pytest.mark.unit
def test_incremental_report_merge_adds_missing_candidate_and_reranks_task():
    existing = schemas.EvaluationResponse(
        job_id="outcome-1",
        job_title="Build AI systems",
        fit_score=0.55,
        capability_score=0.55,
        evidence_confidence=0.6,
        production_readiness=0.4,
        verification_status="verified",
        work_allocation=[
            schemas.WorkAllocation(
                task_id="task-1",
                task_title="Build RAG workflow",
                recommended_candidate="old@example.com",
                confidence=0.55,
                reasons=["Old candidate was best"],
                evidence=[],
                top_candidates=[
                    schemas.CandidateScore(
                        candidate_id="old@example.com",
                        score=0.55,
                        justification="Old evidence",
                        evidence=[],
                    )
                ],
            )
        ],
        global_signals_used=["tests_present"],
        risk_flags=[],
        human_action_required=True,
        candidate_summaries=[
            schemas.CandidateSummary(
                candidate_id="old@example.com",
                overall_score=0.55,
                capability_score=0.55,
                evidence_confidence=0.6,
                production_readiness=0.4,
                verification_status="verified",
                tasks_won=1,
                confidence_rating="Medium",
                risk_flags=[],
            )
        ],
    )
    delta = schemas.EvaluationResponse(
        job_id="outcome-1",
        job_title="Build AI systems",
        fit_score=0.72,
        capability_score=0.72,
        evidence_confidence=0.7,
        production_readiness=0.5,
        verification_status="verified",
        work_allocation=[
            schemas.WorkAllocation(
                task_id="task-1",
                task_title="Build RAG workflow",
                recommended_candidate="new@example.com",
                confidence=0.72,
                reasons=["New candidate is stronger"],
                evidence=[],
                top_candidates=[
                    schemas.CandidateScore(
                        candidate_id="new@example.com",
                        score=0.72,
                        justification="New evidence",
                        evidence=[],
                    )
                ],
            )
        ],
        global_signals_used=["readme_quality_score"],
        risk_flags=[],
        human_action_required=True,
        candidate_summaries=[
            schemas.CandidateSummary(
                candidate_id="new@example.com",
                overall_score=0.72,
                capability_score=0.72,
                evidence_confidence=0.7,
                production_readiness=0.5,
                verification_status="verified",
                tasks_won=1,
                confidence_rating="High",
                risk_flags=[],
            )
        ],
    )

    merged = bulk._merge_evaluation_response(existing, delta)

    assert [item.candidate_id for item in merged.candidate_summaries] == [
        "new@example.com",
        "old@example.com",
    ]
    assert merged.work_allocation[0].recommended_candidate == "new@example.com"
    assert [item.candidate_id for item in merged.work_allocation[0].top_candidates] == [
        "new@example.com",
        "old@example.com",
    ]
    assert merged.global_signals_used == ["readme_quality_score", "tests_present"]


@pytest.mark.integration
def test_staged_job_evaluation_refreshes_reports_with_later_candidates(db_session, monkeypatch):
    job_id = "job-staged-eval"
    outcomes = [
        Outcome(
            id="outcome-staged-1",
            job_id=job_id,
            title="Build AI workflow",
            description="Candidate can build a useful AI workflow.",
            version=1,
            status="active",
        ),
        Outcome(
            id="outcome-staged-2",
            job_id=job_id,
            title="Ship backend service",
            description="Candidate can expose the AI workflow through reliable APIs.",
            version=1,
            status="active",
        ),
    ]
    job = Job(
        id=job_id,
        title="AI Engineer Intern",
        description="Evaluate staged candidates reliably.",
        company="SignalStack",
        location="Remote",
        status="active",
    )
    invite = Invite(
        id="invite-staged",
        token="token-staged",
        job_id=job_id,
        status="active",
        expires_at=utc_now() + timedelta(days=7),
    )
    db_session.add(job)
    db_session.add_all(outcomes)
    db_session.add_all([
        Task(
            id="task-staged-1",
            outcome_id="outcome-staged-1",
            name="Build review flow",
            priority="High",
            weight=1.0,
            version=1,
        ),
        Task(
            id="task-staged-2",
            outcome_id="outcome-staged-2",
            name="Expose API",
            priority="High",
            weight=1.0,
            version=1,
        ),
    ])
    db_session.add(invite)
    db_session.commit()

    monkeypatch.setattr(bulk, "SessionLocal", lambda: _NoCloseSession(db_session))
    monkeypatch.setattr(bulk, "SignalExtractor", _FakeExtractor)
    monkeypatch.setattr(bulk, "Evaluator", _FakeEvaluator)

    _add_submission_with_proofs(db_session, invite, job_id, outcomes, "cand-a")
    _add_submission_with_proofs(db_session, invite, job_id, outcomes, "cand-b")

    first_result = bulk.evaluate_job_applications_sync(job_id)

    assert first_result["evaluated"] == 2
    assert first_result["evaluations_created"] == 2
    for outcome in outcomes:
        latest = db_session.query(Evaluation).filter(
            Evaluation.outcome_id == outcome.id,
        ).order_by(Evaluation.created_at.desc()).first()
        candidate_ids = {
            item["candidate_id"]
            for item in latest.evaluation_json["candidate_summaries"]
        }
        assert candidate_ids == {"cand-a@example.com", "cand-b@example.com"}

    _add_submission_with_proofs(db_session, invite, job_id, outcomes, "cand-c")

    second_result = bulk.evaluate_job_applications_sync(job_id)

    assert second_result["evaluated"] == 1
    assert second_result["deep_evaluated_candidates"] == 3
    assert second_result["evaluations_created"] == 2
    progress = bulk.get_job_evaluation_progress(db_session, job_id)
    assert progress["evaluated_count"] == 3
    assert progress["outcomes_evaluated"] == 2

    for outcome in outcomes:
        latest = db_session.query(Evaluation).filter(
            Evaluation.outcome_id == outcome.id,
        ).order_by(Evaluation.created_at.desc()).first()
        candidate_ids = {
            item["candidate_id"]
            for item in latest.evaluation_json["candidate_summaries"]
        }
        assert candidate_ids == {"cand-a@example.com", "cand-b@example.com", "cand-c@example.com"}

        status = next(
            item for item in progress["outcome_statuses"]
            if item["outcome_id"] == outcome.id
        )
        assert status["latest_evaluation_id"] == latest.id
        assert status["report_candidate_count"] == 3


def test_progress_marks_partial_latest_report_as_stale(db_session):
    job_id = "job-stale-report"
    outcome = Outcome(
        id="outcome-stale-report",
        job_id=job_id,
        title="Productionize AI Backend Services",
        description="Build backend services",
        status="active",
    )
    job = Job(
        id=job_id,
        title="AI Engineer Intern",
        description="Build AI systems",
        company="SignalStack",
        location="Remote",
        status="active",
    )
    invite = Invite(
        id="invite-stale-report",
        token="token-stale-report",
        job_id=job_id,
        status="active",
        expires_at=utc_now() + timedelta(days=7),
    )
    db_session.add_all([job, outcome, invite])
    db_session.commit()

    for candidate_id, score in [("manu", 54.0), ("johny", 25.0), ("chinmaisd", 56.0)]:
        _add_submission_with_proofs(db_session, invite, job_id, [outcome], candidate_id, status="evaluated")
        db_session.add(JobCandidate(
            id=f"jc-{candidate_id}",
            job_id=job_id,
            candidate_id=f"{candidate_id}@example.com",
            status="evaluated",
            evaluation_score=score,
            evaluation_data={
                "submission": {
                    "candidate_name": candidate_id,
                    "candidate_email": f"{candidate_id}@example.com",
                },
                "signals": {},
            },
        ))
    db_session.add(Evaluation(
        job_id=outcome.id,
        outcome_id=outcome.id,
        status="completed",
        fit_score=0.55,
        evaluation_json={
            "candidate_summaries": [
                {"candidate_id": "manu@example.com", "overall_score": 0.54},
                {"candidate_id": "chinmaisd@example.com", "overall_score": 0.56},
            ],
        },
    ))
    db_session.commit()

    progress = bulk.get_job_evaluation_progress(db_session, job_id)
    status = progress["outcome_statuses"][0]

    assert progress["evaluated_count"] == 3
    assert progress["outcomes_evaluated"] == 0
    assert status["status"] == "stale"
    assert status["report_candidate_count"] == 2
    assert status["report_expected_candidate_count"] == 3
    assert status["report_missing_candidate_count"] == 1
