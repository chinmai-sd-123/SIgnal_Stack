from pydantic import BaseModel
from typing import Dict, Optional, Any

class FeedbackCreate(BaseModel):
    job_id: str
    evaluation_id: str
    result: str # success | failure
    metrics: Dict[str, Any]
    notes: Optional[str] = None

class SignalWeightResponse(BaseModel):
    signal_name: str
    weight: float
    task_context: Optional[str] = None

class TaskWeightFeedbackRequest(BaseModel):
    job_id: str
    task_name: str
    direction: str = "boost"  # "boost" (hired because of this) | "reduce" (rejected because of this) | "penalize" (rejected because of this failure)
    # Actually, "boost" = this was good. "penalize" = this was bad.
    # If rejected because of X, X weight should INCREASE (it's important).
    # If hired because of X, X weight likely stays high or increases slightly?
    # User logic: "The candidate failed System Design, so increase the weight of System Design for future candidates".
    # So "direction" -> "increase_importance" | "decrease_importance".
    # Let's keep it simple: "boost" = increase weight.
    reason: Optional[str] = None
