from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List
import uuid

from app.config.database import get_db
from app.models import job as job_models
from app.models.job_candidate import JobCandidate
from app.schemas import job as job_schemas
from app.utils.slug_utils import slugify
from app.utils.time_utils import utc_now
from app.services.shortlist_service import ShortlistService

router = APIRouter()


@router.post("/jobs", response_model=job_schemas.JobResponse)
def create_job(job_data: job_schemas.JobCreate, db: Session = Depends(get_db)):
    """Create a new job posting."""
    job_id = str(uuid.uuid4())
    title_slug = slugify(job_data.title)
    company_slug = slugify(job_data.company)
    slug = f"{title_slug}-{company_slug}-{job_id[:8]}"
    
    db_job = job_models.Job(
        id=job_id,
        title=job_data.title,
        description=job_data.description,
        company=job_data.company,
        location=job_data.location,
        category=job_data.category,
        subcategory=job_data.subcategory,
        job_type=job_data.job_type,
        salary_min=job_data.salary_min,
        salary_max=job_data.salary_max,
        currency=job_data.currency,
        slug=slug,
        company_slug=company_slug,
        location_slug=slugify(job_data.location),
        category_slug=slugify(job_data.category),
        subcategory_slug=slugify(job_data.subcategory) if job_data.subcategory else None,
        status="active",
        created_at=utc_now(),
        last_refreshed_at=utc_now()
    )
    
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


@router.get("/jobs", response_model=List[job_schemas.JobResponse])
def list_jobs(include_archived: bool = False, db: Session = Depends(get_db)):
    """List all jobs. By default, excludes archived jobs."""
    query = db.query(job_models.Job).options(
        joinedload(job_models.Job.outcomes)
    )
    
    if not include_archived:
        query = query.filter(job_models.Job.status != "archived")
    
    jobs = query.order_by(job_models.Job.created_at.desc()).all()
    return jobs


@router.patch("/jobs/{job_id}/status")
def update_job_status(
    job_id: str,
    status_data: dict,
    db: Session = Depends(get_db)
):
    """Update job status (closed/archived)"""
    job = db.query(job_models.Job).filter(job_models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    new_status = status_data.get("status")
    if new_status not in ["active", "closed", "archived"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    job.status = new_status
    db.commit()
    db.refresh(job)
    
    return {"message": f"Job status updated to {new_status}", "job": job}


# ============================================================================
# SHORTLIST MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/jobs/{job_id}/apply")
def apply_to_job(job_id: str, candidate: dict, db: Session = Depends(get_db)):
    """Candidate applies for a job"""
    result = ShortlistService.apply_to_job(
        db=db,
        job_id=job_id,
        candidate_id=candidate.get("candidate_id")
    )
    return result


@router.post("/jobs/{job_id}/candidates/{candidate_id}/evaluate")
def evaluate_candidate(
    job_id: str,
    candidate_id: str,
    evaluation: dict,
    db: Session = Depends(get_db)
):
    """Store evaluation results for a candidate"""
    # Find job candidate record
    job_candidate = db.query(JobCandidate).filter(
        JobCandidate.job_id == job_id,
        JobCandidate.candidate_id == candidate_id
    ).first()
    
    if not job_candidate:
        raise HTTPException(status_code=404, detail="Candidate application not found")
    
    result = ShortlistService.evaluate_candidate(
        db=db,
        job_candidate_id=job_candidate.id,
        evaluation_score=evaluation.get("score"),
        outcome_coverage=evaluation.get("coverage"),
        evaluation_data=evaluation.get("data")
    )
    return result


@router.patch("/jobs/{job_id}/candidates/{candidate_id}/status")
def update_candidate_status(
    job_id: str,
    candidate_id: str,
    status_update: dict,
    db: Session = Depends(get_db)
):
    """
    Update candidate status (recruiter decision).
    Used when recruiter clicks 'Proceed to Interview' or 'Reject'.
    """
    # Find job candidate record
    job_candidate = db.query(JobCandidate).filter(
        JobCandidate.job_id == job_id,
        JobCandidate.candidate_id == candidate_id
    ).first()
    
    if not job_candidate:
        raise HTTPException(status_code=404, detail="Candidate application not found")
    
    new_status = status_update.get("status")
    
    # Validate status
    valid_statuses = ["shortlisted", "rejected"]
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    # Update status
    job_candidate.status = new_status
    if new_status == "shortlisted":
        job_candidate.shortlisted_at = utc_now()
    
    db.commit()
    db.refresh(job_candidate)
    
    return {
        "success": True,
        "candidate_id": candidate_id,
        "status": new_status,
        "message": f"Candidate {'shortlisted' if new_status == 'shortlisted' else 'rejected'}"
    }


@router.get("/jobs/{job_id}/shortlist")
def get_shortlist(job_id: str, auto_select: bool = False, db: Session = Depends(get_db)):
    """Generate and retrieve shortlist with recommendations"""
    result = ShortlistService.generate_shortlist(
        db=db,
        job_id=job_id,
        auto_select=auto_select
    )
    return result


@router.patch("/jobs/{job_id}/shortlist")
def update_shortlist(job_id: str, shortlist: dict, db: Session = Depends(get_db)):
    """Manually update shortlist selection"""
    result = ShortlistService.update_shortlist(
        db=db,
        job_id=job_id,
        shortlisted_candidate_ids=shortlist.get("candidate_ids", [])
    )
    return result


@router.post("/jobs/{job_id}/finalize-shortlist")
def finalize_shortlist(job_id: str, db: Session = Depends(get_db)):
    """
    Finalize shortlist and close applications.
    This transitions job status to 'closed'.
    """
    result = ShortlistService.finalize_shortlist(db=db, job_id=job_id)
    return result


@router.get("/jobs/{job_id}", response_model=job_schemas.JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    """Get a single job by ID."""
    job = db.query(job_models.Job).filter(job_models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/jobs/{job_id}/outcomes")
def get_job_outcomes(job_id: str, db: Session = Depends(get_db)):
    """Get all outcomes for a specific job with their tasks."""
    from app.models import outcome as outcome_models
    from app.models import task as task_models
    
    job = db.query(job_models.Job).filter(job_models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    outcomes = db.query(outcome_models.Outcome).filter(
        outcome_models.Outcome.job_id == job_id
    ).all()
    
    result = []
    for o in outcomes:
        # Fetch tasks for this outcome
        tasks = db.query(task_models.Task).filter(
            task_models.Task.outcome_id == o.id
        ).all()
        
        result.append({
            "id": o.id,
            "title": o.title,
            "description": o.description,
            "status": o.status,
            "company": o.company,
            "location": o.location,
            "tasks": [{"id": t.id, "name": t.name, "weight": t.weight} for t in tasks]
        })
    
    return result


@router.delete("/jobs/{job_id}")
def delete_job(
    job_id: str, 
    hard_delete: bool = False,
    db: Session = Depends(get_db)
):
    """
    Delete or archive a job.
    - Default (soft delete): Sets status to 'archived', hides from listings
    - Hard delete: Permanently removes from database (only if no outcomes exist)
    """
    job = db.query(job_models.Job).filter(job_models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if hard_delete:
        # Check if job has any outcomes
        from app.models import outcome as outcome_models
        outcomes_count = db.query(outcome_models.Outcome).filter(
            outcome_models.Outcome.job_id == job_id
        ).count()
        
        if outcomes_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot permanently delete job with {outcomes_count} outcome(s). Archive it instead or delete outcomes first."
            )
        
        # Permanent delete (only if no outcomes)
        db.delete(job)
        db.commit()
        return {"message": "Job permanently deleted", "job_id": job_id, "type": "hard_delete"}
    else:
        # Soft delete - archive the job
        job.status = "archived"
        job.last_refreshed_at = utc_now()
        db.commit()
        return {"message": "Job archived successfully", "job_id": job_id, "type": "archive"}

