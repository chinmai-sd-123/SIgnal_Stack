from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import datetime
from .outcome import OutcomeResponse
from .proof import ProofCreate, Evidence

class EvaluateRequest(BaseModel):
    request_id: str
    outcome: OutcomeResponse
    proofs: List[ProofCreate]
    options: Optional[Dict[str, Any]] = None

class EvaluationTrigger(BaseModel):
    job_id: str

# NEW: Score for a single candidate on a single task
class CandidateScore(BaseModel):
    candidate_id: str
    score: float
    justification: str

# NEW: Summary of a candidate across all tasks
class CandidateSummary(BaseModel):
    candidate_id: str
    overall_score: float  # Average score across all tasks
    tasks_won: int        # Number of tasks where this candidate is best
    dimensions: Optional[Dict[str, float]] = None  # Radar chart data
    confidence_rating: str = "Medium"  # "High", "Medium", "Low"

class WorkAllocation(BaseModel):
    task_id: str
    task_title: str
    recommended_candidate: str
    confidence: float
    reasons: List[str]
    evidence: List[Evidence]
    # NEW: Top candidates ranked for this task
    top_candidates: List[CandidateScore] = []

class EvaluationResponse(BaseModel):
    job_id: str
    job_title: Optional[str] = None
    fit_score: float
    work_allocation: List[WorkAllocation]
    global_signals_used: List[str]
    risk_flags: List[str]
    human_action_required: bool
    dimensions: Optional[Dict[str, float]] = None  # Global (legacy, can be removed later)
    raw_output: Optional[Dict[str, Any]] = None
    # NEW: Per-candidate performance summary for dashboard
    candidate_summaries: List[CandidateSummary] = []

class EvaluationSummary(BaseModel):
    job_id: str
    outcome_title: str
    fit_score: float
    human_action_required: bool
    risk_flags: List[str]
    created_at: datetime.datetime
