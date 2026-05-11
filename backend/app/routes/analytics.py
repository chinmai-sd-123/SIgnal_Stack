from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.feedback import Feedback
from app.models.outcome import Outcome

from typing import List, Dict, Any
import json

router = APIRouter()

@router.get("/decisions", response_model=List[Dict[str, Any]])
def get_hiring_decisions(db: Session = Depends(get_db)):
    """
    Get a history of all human hiring decisions.
    """
    # Join Feedback and Outcome
    results = db.query(Feedback, Outcome).join(Outcome, Feedback.job_id == Outcome.id).order_by(Feedback.created_at.desc()).all()
    
    history = []
    for feedback, outcome in results:
        # Parse metrics safely
        metrics = feedback.metrics_json or {}
        
        # Determine candidate name
        candidate = metrics.get('selected_candidate', 'Unknown')
        
        # Determine action
        action_raw = metrics.get('action_taken', 'unknown')
        action_label = "Hired" if "hire" in action_raw.lower() else "Rejected"
        
        history.append({
            "id": feedback.id,
            "date": feedback.created_at,
            "job_title": outcome.title,
            "company": outcome.company,
            "candidate": candidate,
            "outcome_id": outcome.id,
            "decision": action_label,
            "raw_action": action_raw
        })
        
    return history

@router.get("/metrics", response_model=Dict[str, Any])
def get_analytics_metrics(db: Session = Depends(get_db)):
    """
    Get high-level hiring metrics.
    """
    feedbacks = db.query(Feedback).all()
    outcomes = db.query(Outcome).count()
    
    total_decisions = len(feedbacks)
    hired_count = 0
    rejected_count = 0
    
    for f in feedbacks:
        metrics = f.metrics_json or {}
        action = metrics.get('action_taken', '').lower()
        if 'hire' in action:
            hired_count += 1
        elif 'reject' in action:
            rejected_count += 1
            
    acceptance_rate = (hired_count / total_decisions * 100) if total_decisions > 0 else 0
    
    return {
        "total_active_jobs": outcomes,
        "total_candidates_processed": total_decisions, # Proxy for now
        "total_hired": hired_count,
        "acceptance_rate": round(acceptance_rate, 1)
    }
