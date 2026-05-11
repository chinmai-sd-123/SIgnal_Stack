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


class _Proof:
    def __init__(self, invite_submission_id, outcome_id="outcome-1"):
        self.outcome_id = outcome_id
        self.payload_json = {"invite_submission_id": invite_submission_id}


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
