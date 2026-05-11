from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
import app.schemas as schemas
from app.config.database import get_db
from app.services import crud
from app.pipeline.feedback import FeedbackLoop

router = APIRouter(tags=["Feedback"])

@router.post("/plugin/feedback")
def submit_feedback(feedback: schemas.FeedbackCreate, db: Session = Depends(get_db)):
    # Store feedback
    crud.create_feedback(db, feedback)
    
    # Mark Evaluation as Complete (Human Action Taken)
    crud.mark_evaluation_complete(db, feedback.job_id, feedback.metrics)
    
    # Trigger Learning Loop (Update Weights)
    loop = FeedbackLoop(db)
    changes = loop.process_feedback(feedback)
        
    return {"status": "feedback_recorded", "changes": changes}

@router.put("/feedback/reset/{job_id}")
def reset_decision(job_id: str, db: Session = Depends(get_db)):
    """Reset the hiring decision for a job, allowing a new decision to be made."""
    result = crud.reset_evaluation_decision(db, job_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Evaluation not found for this job")
    
    # Revert any task learning associated with this job
    loop = FeedbackLoop(db)
    reverted_changes = loop.revert_task_feedback(job_id)

    # Create audit log
    crud.create_audit_log(db, "Evaluation", job_id, "decision_reset", {
        "reason": "User requested to change decision",
        "weight_reverts": reverted_changes
    })
    
    return {"status": "decision_reset", "job_id": job_id}

@router.post("/feedback/task-weight")
def trigger_task_learning(request: schemas.TaskWeightFeedbackRequest, db: Session = Depends(get_db)):
    """
    Trigger the Learning Loop to adjust Task weights in the Master Template
    based on feedback from a specific job instance.
    """
    loop = FeedbackLoop(db)
    try:
        result = loop.process_task_feedback(request)
        return result
    except ValueError as e:
        # Check if it is a nice error or crash
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/admin/signal-weights", response_model=List[schemas.SignalWeightResponse])
def get_signal_weights(db: Session = Depends(get_db)):
    weights = crud.get_signal_weights(db)
    return [schemas.SignalWeightResponse(
        signal_name=w.signal_name,
        weight=w.weight,
        task_context=w.task_id
    ) for w in weights]

@router.get("/admin/audit-logs")
def get_audit_logs(db: Session = Depends(get_db)):
    logs = crud.get_audit_logs(db)
    return [{"id": l.id, "entity_type": l.entity_type, "entity_id": l.entity_id, "action": l.action, "details": l.details_json, "created_at": l.created_at.isoformat()} for l in logs]

@router.get("/admin/feedback")
def get_feedback_list(db: Session = Depends(get_db)):
    feedback = crud.get_feedback_list(db)
    return [{"id": f.id, "job_id": f.job_id, "result": f.result, "metrics": f.metrics_json, "created_at": f.created_at.isoformat()} for f in feedback]
