import pytest

from app.models.invite import InviteSubmission
from app.models.job_candidate import JobCandidate
from app.services import bulk_evaluation_service as bulk


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
