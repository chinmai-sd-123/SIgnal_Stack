from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid

from app.config.database import get_db
from app.models.invite import Invite
from app.models.job import Job

router = APIRouter(tags=["Invites"])

INVITE_EXPIRY_DAYS = 7


# ─── Recruiter endpoints ────────────────────────────────────────────────────

@router.post("/jobs/{job_id}/invites")
def create_invite(job_id: str, db: Session = Depends(get_db)):
    """Generate a new invite link for a job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    invite = Invite(
        id=str(uuid.uuid4()),
        token=str(uuid.uuid4()),
        job_id=job_id,
        expires_at=datetime.utcnow() + timedelta(days=INVITE_EXPIRY_DAYS),
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
    }


@router.get("/jobs/{job_id}/invites")
def list_invites(job_id: str, db: Session = Depends(get_db)):
    """List all invites for a job (recruiter view)."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    invites = db.query(Invite).filter(Invite.job_id == job_id).order_by(Invite.created_at.desc()).all()

    return [
        {
            "id": inv.id,
            "token": inv.token,
            "status": inv.status,
            "candidate_name": inv.candidate_name,
            "candidate_email": inv.candidate_email,
            "github_username": inv.github_username,
            "linkedin_url": inv.linkedin_url,
            "resume_url": inv.resume_url,
            "repo_url": inv.repo_url,
            "leetcode_username": inv.leetcode_username,
            "context": inv.context,
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
            "submitted_at": inv.submitted_at.isoformat() if inv.submitted_at else None,
            "is_expired": inv.expires_at < datetime.utcnow() if inv.expires_at else False,
        }
        for inv in invites
    ]


@router.delete("/invites/{invite_id}")
def revoke_invite(invite_id: str, db: Session = Depends(get_db)):
    """Revoke/delete an invite."""
    invite = db.query(Invite).filter(Invite.id == invite_id).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")

    db.delete(invite)
    db.commit()
    return {"message": "Invite revoked", "id": invite_id}


# ─── Candidate (public) endpoints ───────────────────────────────────────────

@router.get("/invites/{token}")
def get_invite(token: str, db: Session = Depends(get_db)):
    """Public endpoint. Candidate opens the link — returns job info."""
    invite = db.query(Invite).filter(Invite.token == token).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")

    if invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="This invite link has expired")

    if invite.status != "pending":
        raise HTTPException(status_code=400, detail="This invite has already been used")

    job = db.query(Job).filter(Job.id == invite.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job no longer exists")

    # Fetch outcomes for the job
    from app.models.outcome import Outcome
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
    """Candidate submits their proof via the invite link."""
    invite = db.query(Invite).filter(Invite.token == token).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")

    if invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="This invite link has expired")

    if invite.status != "pending":
        raise HTTPException(status_code=400, detail="This invite has already been used")

    # Save candidate info
    invite.candidate_name = data.get("candidate_name", "")
    invite.candidate_email = data.get("candidate_email", "")
    invite.github_username = data.get("github_username", "")
    invite.repo_url = data.get("repo_url", "")
    invite.linkedin_url = data.get("linkedin_url", "")
    invite.resume_url = data.get("resume_url", "")
    invite.leetcode_username = data.get("leetcode_username", "")
    invite.context = data.get("context", "")
    invite.status = "submitted"
    invite.submitted_at = datetime.utcnow()

    db.commit()
    db.refresh(invite)

    # Trigger evaluation pipeline if repo_url is provided
    if invite.repo_url:
        try:
            from app.services.worker_queue import worker_queue

            candidate_id = invite.github_username or invite.candidate_email or f"invite_{invite.id[:8]}"

            # Submit proof through the existing pipeline
            from app.pipeline.proof import ProofPipeline
            pipeline = ProofPipeline(db)
            pipeline.submit_proof(
                job_id=invite.job_id,
                candidate_id=candidate_id,
                proof_type="github",
                payload={
                    "repo_url": invite.repo_url,
                    "leetcode_username": invite.leetcode_username,
                    "context": invite.context,
                },
            )
        except Exception as e:
            # Don't fail the submission if pipeline has issues
            print(f"[WARN] Evaluation pipeline error for invite {invite.id}: {e}")

    return {
        "message": "Application submitted successfully",
        "invite_id": invite.id,
        "status": invite.status,
    }
