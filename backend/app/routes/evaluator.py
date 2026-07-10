from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List
import time
import app.schemas as schemas
from app.config.database import get_db
from app.models.job import Job
from app.models.recruiter import Recruiter
from app.monitoring import track_evaluation_complete, track_evaluation_start
from app.services import crud
from app.services.auth import ensure_job_access, get_current_recruiter
from app.pipeline.evaluator import Evaluator
from app.pipeline.scoring_engine import load_signal_weights
from app.pipeline.signal_extractor import SignalExtractor
import app.models as models

router = APIRouter(tags=["Evaluator"])

@router.post("/plugin/evaluate")
def evaluate(
    request: schemas.EvaluateRequest,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    started_at = time.perf_counter()
    track_evaluation_start()
    success = False
    try:
        if getattr(request.outcome, "job_id", None):
            job = db.query(Job).filter(Job.id == request.outcome.job_id).first()
            ensure_job_access(job, current)

        # 1. Extract Signals
        signals_map = {}
        extractor = SignalExtractor()
        for proof in request.proofs:
            signals = extractor.extract_signals(proof)
            signals_map[proof.candidate_id] = signals

        # 2. Evaluate using Allocation Engine (with learned signal weights)
        evaluator = Evaluator()
        weights = load_signal_weights(db)
        evaluation = evaluator.evaluate(request.outcome, request.proofs, signals_map, weights=weights)

        # 3. Store Evaluation (Persist the result)
        crud.create_evaluation(db, evaluation)

        # 4. Audit Log
        crud.create_audit_log(db, "evaluation", evaluation.job_id, "completed", {"fit_score": evaluation.fit_score, "candidates": [p.candidate_id for p in request.proofs]})

        success = True
        return {
            "job_id": evaluation.job_id,
            "status": "completed",
            "evaluation": evaluation
        }
    finally:
        track_evaluation_complete(time.perf_counter() - started_at, success=success)

@router.get("/evaluations", response_model=List[schemas.EvaluationSummary])
def get_evaluations(
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    query = db.query(models.Evaluation, models.Outcome).join(
        models.Outcome,
        models.Evaluation.outcome_id == models.Outcome.id,
    )
    if current.role != "admin":
        query = query.join(Job, models.Outcome.job_id == Job.id).filter(Job.recruiter_id == current.id)

    results = query.order_by(models.Evaluation.created_at.desc()).all()
    return [
        {
            "job_id": eval_model.job_id,
            "outcome_title": outcome_model.title,
            "fit_score": eval_model.fit_score,
            "human_action_required": (eval_model.evaluation_json or {}).get("human_action_required", True),
            "risk_flags": (eval_model.evaluation_json or {}).get("risk_flags", []),
            "created_at": eval_model.created_at,
        }
        for eval_model, outcome_model in results
    ]

@router.get("/plugin/status/{job_id}")
def get_status(
    job_id: str,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    # Return the LATEST evaluation for this outcome (most recent run)
    # Note: job_id in evaluation context is actually outcome_id
    eval_db = db.query(models.Evaluation).filter(
        or_(
            models.Evaluation.job_id == job_id,
            models.Evaluation.outcome_id == job_id,
        )
    ).order_by(models.Evaluation.created_at.desc()).first()
    
    # Get outcome title (job_id is actually outcome_id in this context)
    outcome_db = db.query(models.Outcome).filter(models.Outcome.id == job_id).first()
    if outcome_db and outcome_db.job_id:
        job = db.query(Job).filter(Job.id == outcome_db.job_id).first()
        ensure_job_access(job, current)
    
    if eval_db:
        response = dict(eval_db.evaluation_json)
        # Inject outcome title
        if outcome_db:
            response['job_title'] = outcome_db.title
            
        return {"job_id": job_id, "status": "completed", "evaluation": response}
    return {"job_id": job_id, "status": "pending"}
