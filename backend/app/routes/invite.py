from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from datetime import timedelta
import uuid

from app.config.database import get_db
from app.models.invite import Invite, InviteSubmission
from app.models.job import Job
from app.models.outcome import Outcome
from app.models.proof import Proof
from app.models.recruiter import Recruiter
from app.services.bulk_evaluation_service import ensure_job_candidate
from app.services.auth import ensure_job_access, get_current_recruiter
from app.services.submission_proof_service import (
    create_proofs_for_submission,
    get_candidate_id,
    proof_payload_for_submission,
)
from app.utils.time_utils import utc_now

router = APIRouter(tags=["Invites"])

INVITE_EXPIRY_DAYS = 7


# ─── Helper: manage proof lifecycle ─────────────────────────────────────────

def _get_candidate_id(submission: InviteSubmission) -> str:
    """Derive a stable candidate_id from submission data."""
    return get_candidate_id(submission)


def _proof_payload_for_submission(submission: InviteSubmission):
    """Build the evaluator payload for an invite submission."""
    return proof_payload_for_submission(submission)


def _create_proofs_for_submission(db: Session, submission: InviteSubmission, job_id: str):
    """Create Proof records across all outcomes for a candidate submission."""
    return create_proofs_for_submission(db, submission, job_id)


def _delete_proofs_for_submission(db: Session, submission: InviteSubmission):
    """Delete all Proof records associated with a submission."""
    outcome_ids = [row[0] for row in db.query(Outcome.id).filter(Outcome.job_id == submission.job_id).all()]
    if not outcome_ids:
        return 0
    proofs = db.query(Proof).filter(Proof.outcome_id.in_(outcome_ids)).all()

    deleted = 0
    for proof in proofs:
        # Only delete proofs that came from invite system
        payload = proof.payload_json or {}
        if payload.get("source") == "invite" and payload.get("invite_submission_id") == submission.id:
            db.delete(proof)
            deleted += 1

    return deleted


def _update_proofs_for_submission(db: Session, submission: InviteSubmission, old_candidate_id: str):
    """Update all Proof records when submission data changes."""
    new_candidate_id = _get_candidate_id(submission)

    # Find proofs linked to this submission
    proofs = db.query(Proof).filter(Proof.candidate_id.in_([old_candidate_id, new_candidate_id])).all()

    for proof in proofs:
        payload = proof.payload_json or {}
        if payload.get("source") == "invite" and payload.get("invite_submission_id") == submission.id:
            # Update candidate_id if it changed
            proof.candidate_id = new_candidate_id
            proof.type = "github" if submission.repo_url else "work_artifact"
            proof.payload_json = _proof_payload_for_submission(submission)


# ─── Recruiter endpoints ────────────────────────────────────────────────────

@router.post("/jobs/{job_id}/invites")
def create_invite(
    job_id: str,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """Generate a reusable invite link for a job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    ensure_job_access(job, current)

    invite = Invite(
        id=str(uuid.uuid4()),
        token=str(uuid.uuid4()),
        job_id=job_id,
        status="active",
        expires_at=utc_now() + timedelta(days=INVITE_EXPIRY_DAYS),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    return {
        "id": invite.id,
        "token": invite.token,
        "job_id": job_id,
        "status": invite.status,
        "expires_at": invite.expires_at.isoformat(),
        "created_at": invite.created_at.isoformat(),
        "submission_count": 0,
    }


@router.get("/jobs/{job_id}/invites")
def list_invites(
    job_id: str,
    response: Response,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """List all invites for a job with their submissions."""
    job = db.query(Job).filter(Job.id == job_id).first()
    ensure_job_access(job, current)

    response.headers["Cache-Control"] = "no-store"
    invites = db.query(Invite).filter(Invite.job_id == job_id).order_by(Invite.created_at.desc()).all()

    result = []
    for inv in invites:
        submissions = db.query(InviteSubmission).filter(
            InviteSubmission.invite_id == inv.id
        ).order_by(InviteSubmission.submitted_at.desc()).all()

        result.append({
            "id": inv.id,
            "token": inv.token,
            "status": inv.status,
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
            "is_expired": inv.expires_at < utc_now() if inv.expires_at else False,
            "submission_count": len(submissions),
            "submissions": [
                {
                    "id": sub.id,
                    "candidate_name": sub.candidate_name,
                    "candidate_email": sub.candidate_email,
                    "github_username": sub.github_username,
                    "repo_url": sub.repo_url,
                    "linkedin_url": sub.linkedin_url,
                    "resume_url": sub.resume_url,
                    "leetcode_username": sub.leetcode_username,
                    "context": sub.context,
                    "status": sub.status,
                    "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
                }
                for sub in submissions
            ],
        })

    return result


@router.delete("/invites/{invite_id}")
def revoke_invite(
    invite_id: str,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """Revoke an invite — also deletes all submissions AND their proofs from outcomes."""
    invite = db.query(Invite).filter(Invite.id == invite_id).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    job = db.query(Job).filter(Job.id == invite.job_id).first()
    ensure_job_access(job, current)

    # First, delete all proofs linked to this invite's submissions
    submissions = db.query(InviteSubmission).filter(InviteSubmission.invite_id == invite.id).all()
    total_proofs_deleted = 0
    for sub in submissions:
        total_proofs_deleted += _delete_proofs_for_submission(db, sub)

    # Then delete the invite (CASCADE deletes submissions)
    db.delete(invite)
    db.commit()

    print(f"[OK] Revoked invite {invite_id}: deleted {len(submissions)} submissions, {total_proofs_deleted} proofs")
    return {
        "message": "Invite revoked",
        "id": invite_id,
        "submissions_deleted": len(submissions),
        "proofs_deleted": total_proofs_deleted,
    }


# ─── Submission management (recruiter) ──────────────────────────────────────

@router.delete("/submissions/{submission_id}")
def delete_submission(
    submission_id: str,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """Delete a single candidate submission and its proofs from all outcomes."""
    submission = db.query(InviteSubmission).filter(InviteSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    job = db.query(Job).filter(Job.id == submission.job_id).first()
    ensure_job_access(job, current)

    # Delete linked proofs first
    proofs_deleted = _delete_proofs_for_submission(db, submission)

    # Delete the submission
    db.delete(submission)
    db.commit()

    print(f"[OK] Deleted submission {submission_id}: {proofs_deleted} proofs removed")
    return {
        "message": "Candidate removed",
        "id": submission_id,
        "proofs_deleted": proofs_deleted,
    }


@router.put("/submissions/{submission_id}")
def update_submission(
    submission_id: str,
    data: dict,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """Edit a candidate's submission details. Also updates linked proofs."""
    submission = db.query(InviteSubmission).filter(InviteSubmission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    job = db.query(Job).filter(Job.id == submission.job_id).first()
    ensure_job_access(job, current)

    # Track old candidate_id before update (for proof relinking)
    old_candidate_id = _get_candidate_id(submission)

    # Update fields
    if "candidate_name" in data:
        submission.candidate_name = data["candidate_name"]
    if "candidate_email" in data:
        submission.candidate_email = data["candidate_email"]
    if "github_username" in data:
        submission.github_username = data["github_username"]
    if "repo_url" in data:
        submission.repo_url = data["repo_url"]
    if "linkedin_url" in data:
        submission.linkedin_url = data["linkedin_url"]
    if "resume_url" in data:
        submission.resume_url = data["resume_url"]
    if "leetcode_username" in data:
        submission.leetcode_username = data["leetcode_username"]
    if "context" in data:
        submission.context = data["context"]

    # Update linked proofs
    _update_proofs_for_submission(db, submission, old_candidate_id)

    db.commit()
    db.refresh(submission)

    print(f"[OK] Updated submission {submission_id}")
    return {
        "id": submission.id,
        "candidate_name": submission.candidate_name,
        "candidate_email": submission.candidate_email,
        "github_username": submission.github_username,
        "repo_url": submission.repo_url,
        "linkedin_url": submission.linkedin_url,
        "resume_url": submission.resume_url,
        "leetcode_username": submission.leetcode_username,
        "context": submission.context,
        "status": submission.status,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
    }


# ─── Candidate (public) endpoints ───────────────────────────────────────────

@router.get("/invites/{token}")
def get_invite(token: str, db: Session = Depends(get_db)):
    """Public endpoint. Candidate opens the link — returns job info."""
    invite = db.query(Invite).filter(Invite.token == token).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")

    if invite.expires_at < utc_now():
        raise HTTPException(status_code=410, detail="This invite link has expired")

    if invite.status != "active":
        raise HTTPException(status_code=400, detail="This invite link is no longer accepting submissions")

    job = db.query(Job).filter(Job.id == invite.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job no longer exists")

    outcomes = db.query(Outcome).filter(Outcome.job_id == job.id).all()

    return {
        "token": invite.token,
        "status": invite.status,
        "expires_at": invite.expires_at.isoformat(),
        "job": {
            "id": job.id,
            "title": job.title,
            "description": job.description,
            "company": job.company,
            "location": job.location,
            "job_type": job.job_type,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "currency": job.currency,
            "category": job.category,
            "outcomes": [
                {"id": o.id, "title": o.title, "description": o.description}
                for o in outcomes
            ],
        },
    }


@router.post("/invites/{token}/submit")
def submit_invite(token: str, data: dict, db: Session = Depends(get_db)):
    """Candidate submits their application via the invite link."""
    invite = db.query(Invite).filter(Invite.token == token).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")

    if invite.expires_at < utc_now():
        raise HTTPException(status_code=410, detail="This invite link has expired")

    if invite.status != "active":
        raise HTTPException(status_code=400, detail="This invite link is no longer accepting submissions")

    # Check for duplicate email on same invite
    candidate_email = data.get("candidate_email", "").strip()
    if candidate_email:
        existing = db.query(InviteSubmission).filter(
            InviteSubmission.invite_id == invite.id,
            InviteSubmission.candidate_email == candidate_email,
        ).first()
        if existing:
            raise HTTPException(status_code=409, detail="You have already submitted an application with this email")

    # Create submission record
    submission = InviteSubmission(
        id=str(uuid.uuid4()),
        invite_id=invite.id,
        job_id=invite.job_id,
        candidate_name=data.get("candidate_name", ""),
        candidate_email=candidate_email,
        github_username=data.get("github_username", ""),
        repo_url=data.get("repo_url", ""),
        linkedin_url=data.get("linkedin_url", ""),
        resume_url=data.get("resume_url", ""),
        leetcode_username=data.get("leetcode_username", ""),
        context=data.get("context", ""),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    # Create Proof records for each outcome
    try:
        created = _create_proofs_for_submission(db, submission, invite.job_id)
        ensure_job_candidate(db, invite.job_id, _get_candidate_id(submission), status="submitted")
        db.commit()
        print(f"[OK] Created {created} proof(s) for submission {submission.id}")
    except Exception as e:
        print(f"[WARN] Failed to create proofs for submission {submission.id}: {e}")

    return {
        "message": "Application submitted successfully",
        "submission_id": submission.id,
        "status": submission.status,
    }
