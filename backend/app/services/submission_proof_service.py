from sqlalchemy.orm import Session

from app.models.invite import InviteSubmission
from app.models.outcome import Outcome
from app.models.proof import Proof


def get_candidate_id(submission: InviteSubmission) -> str:
    """Derive a stable candidate id from invite submission data."""
    return submission.github_username or submission.candidate_email or f"sub_{submission.id[:8]}"


def proof_payload_for_submission(submission: InviteSubmission):
    """Build evaluator payload for an invite submission."""
    return {
        "repo_url": submission.repo_url or "",
        "github_username": submission.github_username or "",
        "leetcode_username": submission.leetcode_username or "",
        "artifact_link": "" if submission.repo_url else (submission.resume_url or ""),
        "resume_url": submission.resume_url or "",
        "context": submission.context or "",
        "candidate_name": submission.candidate_name,
        "candidate_email": submission.candidate_email,
        "linkedin_url": submission.linkedin_url or "",
        "source": "invite",
        "invite_submission_id": submission.id,
    }


def create_proof_for_outcome(db: Session, submission: InviteSubmission, outcome: Outcome) -> bool:
    """Create one proof for one submission/outcome pair if missing."""
    candidate_id = get_candidate_id(submission)

    existing = db.query(Proof).filter(
        Proof.outcome_id == outcome.id,
        Proof.candidate_id == candidate_id,
    ).first()
    if existing:
        return False

    proof = Proof(
        outcome_id=outcome.id,
        candidate_id=candidate_id,
        type="github" if submission.repo_url else "work_artifact",
        payload_json=proof_payload_for_submission(submission),
    )
    db.add(proof)
    return True


def create_proofs_for_submission(db: Session, submission: InviteSubmission, job_id: str) -> int:
    """Create proof records for this submission across all current outcomes."""
    outcomes = db.query(Outcome).filter(Outcome.job_id == job_id).all()
    return sum(1 for outcome in outcomes if create_proof_for_outcome(db, submission, outcome))


def sync_outcome_invite_proofs(db: Session, outcome_id: str) -> int:
    """
    Backfill invite proofs for an outcome.

    This repairs the case where candidates submitted before an outcome was
    created, so the outcome dashboard can still show those candidates.
    """
    outcome = db.query(Outcome).filter(Outcome.id == outcome_id).first()
    if not outcome or not outcome.job_id:
        return 0

    submissions = db.query(InviteSubmission).filter(
        InviteSubmission.job_id == outcome.job_id,
    ).all()

    created = 0
    for submission in submissions:
        if create_proof_for_outcome(db, submission, outcome):
            created += 1

    if created:
        db.commit()
    return created


def sync_job_invite_proofs(db: Session, job_id: str) -> int:
    """Backfill invite proofs for every outcome under a job."""
    outcomes = db.query(Outcome).filter(Outcome.job_id == job_id).all()
    created = 0
    for outcome in outcomes:
        created += sync_outcome_invite_proofs(db, outcome.id)
    return created
