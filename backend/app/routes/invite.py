from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid

from app.config.database import get_db
from app.models.invite import Invite, InviteSubmission
from app.models.job import Job

router = APIRouter(tags=["Invites"])

INVITE_EXPIRY_DAYS = 7


# ─── Recruiter endpoints ────────────────────────────────────────────────────

@router.post("/jobs/{job_id}/invites")
def create_invite(job_id: str, db: Session = Depends(get_db)):
    """Generate a reusable invite link for a job. Multiple candidates can use it."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    invite = Invite(
        id=str(uuid.uuid4()),
        token=str(uuid.uuid4()),
        job_id=job_id,
        status="active",
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
        "submission_count": 0,
    }


@router.get("/jobs/{job_id}/invites")
def list_invites(job_id: str, db: Session = Depends(get_db)):
    """List all invites for a job with their submissions (recruiter view)."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

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
            "is_expired": inv.expires_at < datetime.utcnow() if inv.expires_at else False,
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
def revoke_invite(invite_id: str, db: Session = Depends(get_db)):
    """Revoke/delete an invite and all its submissions."""
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

    if invite.status != "active":
        raise HTTPException(status_code=400, detail="This invite link is no longer accepting submissions")

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
    """Candidate submits their application via the invite link. Link stays reusable."""
    invite = db.query(Invite).filter(Invite.token == token).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")

    if invite.expires_at < datetime.utcnow():
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

    # Create Proof records for each outcome in the job so candidates
    # appear in OutcomeDashboard and can be evaluated
    try:
        from app.models.outcome import Outcome
        from app.models.proof import Proof

        candidate_id = submission.github_username or submission.candidate_email or f"sub_{submission.id[:8]}"
        outcomes = db.query(Outcome).filter(Outcome.job_id == invite.job_id).all()

        for outcome in outcomes:
            # Check if proof already exists for this candidate + outcome
            existing_proof = db.query(Proof).filter(
                Proof.outcome_id == outcome.id,
                Proof.candidate_id == candidate_id,
            ).first()
            if existing_proof:
                continue

            proof = Proof(
                outcome_id=outcome.id,
                candidate_id=candidate_id,
                type="github" if submission.repo_url else "work_artifact",
                payload_json={
                    "repo_url": submission.repo_url or "",
                    "leetcode_username": submission.leetcode_username or "",
                    "artifact_link": submission.resume_url or "",
                    "context": submission.context or "",
                    "candidate_name": submission.candidate_name,
                    "candidate_email": submission.candidate_email,
                    "linkedin_url": submission.linkedin_url or "",
                    "source": "invite",
                    "invite_submission_id": submission.id,
                },
            )
            db.add(proof)

        db.commit()
        print(f"[OK] Created {len(outcomes)} proof(s) for invite submission {submission.id}")
    except Exception as e:
        print(f"[WARN] Failed to create proofs for submission {submission.id}: {e}")

    return {
        "message": "Application submitted successfully",
        "submission_id": submission.id,
        "status": submission.status,
    }

