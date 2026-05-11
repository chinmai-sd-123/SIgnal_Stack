from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import app.schemas as schemas
from app.config.database import get_db
from app.services import crud
from app.pipeline.outcome import OutcomePipeline

router = APIRouter(tags=["Outcome"])

@router.get("/outcomes", response_model=List[schemas.OutcomeResponse])
def get_outcomes(category: str = None, db: Session = Depends(get_db)):
    outcomes = crud.get_outcomes(db, category=category)
    return outcomes

@router.post("/outcomes", response_model=schemas.OutcomeResponse)
def create_outcome(outcome: schemas.OutcomeCreate, db: Session = Depends(get_db)):
    pipeline = OutcomePipeline(db)
    # No need to check for existing ID as we generate a new one
    result = pipeline.create_outcome(outcome)
    
    # Audit Log
    crud.create_audit_log(db, "outcome", result.id, "created", {"title": outcome.title})
    return result

@router.get("/outcomes/templates", response_model=List[schemas.OutcomeResponse])
def get_outcome_templates(db: Session = Depends(get_db)):
    """List all available Outcome Templates."""
    return crud.get_outcome_templates(db)

@router.get("/outcomes/{outcome_id}", response_model=schemas.OutcomeResponse)
def get_outcome(outcome_id: str, db: Session = Depends(get_db)):
    pipeline = OutcomePipeline(db)
    outcome = pipeline.get_outcome(outcome_id)
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")
    return outcome

@router.post("/outcomes/template", response_model=schemas.OutcomeResponse)
def create_outcome_template(outcome: schemas.OutcomeCreate, db: Session = Depends(get_db)):
    """Create a new reusable Outcome Template (Master)."""
    outcome.is_template = 1 # Force template flag
    pipeline = OutcomePipeline(db)
    result = pipeline.create_outcome(outcome)
    return result

@router.post("/jobs/{job_id}/instantiate", response_model=schemas.OutcomeResponse)
def instantiate_job_from_template(job_id: str, template_id: str, db: Session = Depends(get_db)):
    """Create a new Job/Outcome instance from a Template."""
    try:
        result = crud.instantiate_outcome_from_template(db, template_id, job_id)
        crud.create_audit_log(db, "outcome", result.id, "instantiated", {"source_template": template_id, "job_id": job_id})
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
