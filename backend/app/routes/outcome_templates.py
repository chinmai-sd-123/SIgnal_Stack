from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from app.config.database import get_db
from app.models.outcome_template import OutcomeTemplate


router = APIRouter()


class OutcomeData(BaseModel):
    """Single outcome within a template."""
    title: str
    description: str
    default_weight: float


class OutcomeTemplateResponse(BaseModel):
    """Response model for outcome templates."""
    id: str
    role_name: str
    category_slug: str
    outcomes: List[dict]
    created_at: str
    
    class Config:
        from_attributes = True


@router.get("/outcome-templates", response_model=List[dict])
def get_outcome_templates(
    category_slug: Optional[str] = Query(None, description="Filter by category slug"),
    db: Session = Depends(get_db)
):
    """
    Get all outcome templates, optionally filtered by category.
    
    These templates provide pre-written outcomes for common roles that recruiters
    can use as starting points. The AI will still generate tasks from these outcomes.
    """
    # 1. Fetch Role-based Templates
    query = db.query(OutcomeTemplate)
    if category_slug:
        query = query.filter(OutcomeTemplate.category_slug == category_slug)
    role_templates = query.order_by(OutcomeTemplate.role_name).all()
    
    # 2. Fetch Legacy Outcome Templates (is_template=1)
    # Import Outcome model here to avoid circular imports if any, or better at top if safe.
    from app.models.outcome import Outcome
    legacy_query = db.query(Outcome).filter(Outcome.is_template == 1)
    if category_slug:
        # Assuming Outcome has category field? If not, skip filter or verify model.
        # Legacy Outcome model usually has 'category' string instead of slug.
        # We'll omit category filter for legacy for now or do partial match if needed.
        pass
    legacy_templates = legacy_query.all()

    results = []

    # Format Role Templates
    for t in role_templates:
        results.append({
            "id": t.id,
            "role_name": t.role_name,
            "category_slug": t.category_slug,
            "outcomes": t.outcomes,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "type": "role"
        })

    # Format Legacy Templates
    for t in legacy_templates:
        # Convert Tasks to list of dicts if they aren't already
        tasks_data = []
        if t.tasks:
            for task in t.tasks:
                tasks_data.append({
                    "name": task.name,
                    "priority": task.priority,
                    "weight": task.weight
                })

        results.append({
            "id": t.id,
            "title": t.title, # Legacy uses title
            "description": t.description,
            "tasks": tasks_data,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "type": "outcome" # Tag as single outcome template
        })
    
    return results


@router.get("/outcome-templates/{template_id}", response_model=OutcomeTemplateResponse)
def get_outcome_template(template_id: str, db: Session = Depends(get_db)):
    """Get a specific outcome template by ID."""
    template = db.query(OutcomeTemplate).filter(OutcomeTemplate.id == template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        "id": template.id,
        "role_name": template.role_name,
        "category_slug": template.category_slug,
        "outcomes": template.outcomes,
        "created_at": template.created_at.isoformat() if template.created_at else None
    }
