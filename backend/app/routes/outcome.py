from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import app.schemas as schemas
from app.config.database import get_db
from app.services import crud
from app.models.job import Job
from app.models.recruiter import Recruiter
from app.services.auth import ensure_job_access, get_current_recruiter
from app.services.submission_proof_service import sync_outcome_invite_proofs
from app.pipeline.outcome import OutcomePipeline

router = APIRouter(tags=["Outcome"])

@router.get("/outcomes", response_model=List[schemas.OutcomeResponse])
def get_outcomes(
    category: str = None,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    outcomes = crud.get_outcomes(db, category=category)
    if current.role != "admin":
        job_ids = {
            row[0]
            for row in db.query(Job.id).filter(Job.recruiter_id == current.id).all()
        }
        outcomes = [outcome for outcome in outcomes if outcome.job_id in job_ids]
    return outcomes

@router.post("/outcomes", response_model=schemas.OutcomeResponse)
def create_outcome(
    outcome: schemas.OutcomeCreate,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    if outcome.job_id:
        job = db.query(Job).filter(Job.id == outcome.job_id).first()
        ensure_job_access(job, current)
    pipeline = OutcomePipeline(db)
    # No need to check for existing ID as we generate a new one
    result = pipeline.create_outcome(outcome)
    
    # Audit Log
    crud.create_audit_log(db, "outcome", result.id, "created", {"title": outcome.title})
    sync_outcome_invite_proofs(db, result.id)
    return result

@router.get("/outcomes/templates", response_model=List[schemas.OutcomeResponse])
def get_outcome_templates(
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """List all available Outcome Templates."""
    return crud.get_outcome_templates(db)

@router.get("/outcomes/{outcome_id}", response_model=schemas.OutcomeResponse)
def get_outcome(
    outcome_id: str,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    pipeline = OutcomePipeline(db)
    outcome = pipeline.get_outcome(outcome_id)
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")
    if outcome.job_id:
        job = db.query(Job).filter(Job.id == outcome.job_id).first()
        ensure_job_access(job, current)
    return outcome

@router.patch("/outcomes/{outcome_id}", response_model=schemas.OutcomeResponse)
def update_outcome(
    outcome_id: str,
    outcome: schemas.OutcomeUpdate,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    existing = crud.get_outcome(db, outcome_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Outcome not found")
    if existing.job_id:
        job = db.query(Job).filter(Job.id == existing.job_id).first()
        ensure_job_access(job, current)
    result = crud.update_outcome(db, outcome_id, outcome)

    crud.create_audit_log(db, "outcome", result.id, "updated", {"title": result.title})
    sync_outcome_invite_proofs(db, result.id)
    return result

@router.delete("/outcomes/{outcome_id}")
def delete_outcome(
    outcome_id: str,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    existing = crud.get_outcome(db, outcome_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Outcome not found")
    if existing.job_id:
        job = db.query(Job).filter(Job.id == existing.job_id).first()
        ensure_job_access(job, current)

    job_id = existing.job_id
    title = existing.title
    deleted = crud.delete_outcome(db, outcome_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Outcome not found")

    crud.create_audit_log(db, "outcome", outcome_id, "deleted", {"title": title, "job_id": job_id})
    return {"id": outcome_id, "job_id": job_id, "status": "deleted"}

@router.post("/outcomes/template", response_model=schemas.OutcomeResponse)
def create_outcome_template(
    outcome: schemas.OutcomeCreate,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """Create a new reusable Outcome Template (Master)."""
    outcome.is_template = 1 # Force template flag
    pipeline = OutcomePipeline(db)
    result = pipeline.create_outcome(outcome)
    return result

@router.post("/jobs/{job_id}/instantiate", response_model=schemas.OutcomeResponse)
def instantiate_job_from_template(
    job_id: str,
    template_id: str,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """Create a new Job/Outcome instance from a Template."""
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        ensure_job_access(job, current)
        result = crud.instantiate_outcome_from_template(db, template_id, job_id)
        crud.create_audit_log(db, "outcome", result.id, "instantiated", {"source_template": template_id, "job_id": job_id})
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
