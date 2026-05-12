from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.feedback import Feedback
from app.models.outcome import Outcome
from app.models.evaluation import Evaluation

from typing import List, Dict, Any
import json

router = APIRouter()

@router.get("/decisions", response_model=List[Dict[str, Any]])
def get_hiring_decisions(db: Session = Depends(get_db)):
    """
    Get a history of all human hiring decisions.
    """
    results = db.query(Feedback, Outcome, Evaluation).join(
        Outcome,
        Feedback.job_id == Outcome.id,
    ).outerjoin(
        Evaluation,
        Feedback.evaluation_id == Evaluation.id,
    ).order_by(Feedback.created_at.desc()).all()
    
    history = []
    for feedback, outcome, evaluation in results:
        # Parse metrics safely
        metrics = feedback.metrics_json or {}
        
        # Determine candidate name
        selected = metrics.get('selected_candidate')
        selected_list = metrics.get('selected_candidates') or []
        rejected_list = metrics.get('rejected_candidates') or []
        if selected:
            candidate = selected
        elif selected_list:
            candidate = ", ".join(selected_list)
        elif rejected_list:
            candidate = ", ".join(rejected_list)
        else:
            candidate = "All candidates" if metrics.get("action_taken") == "reject_all" else "Unknown"
        
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
            "job_id": outcome.job_id,
            "evaluation_id": evaluation.id if evaluation else feedback.evaluation_id,
            "decision": action_label,
            "raw_action": action_raw,
            "details_path": f"/evaluation/{outcome.id}",
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
