from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session, joinedload
from typing import List
import uuid

from app.config.database import get_db
from app.models import job as job_models
from app.models.job_candidate import JobCandidate
from app.models.recruiter import Recruiter
from app.schemas import job as job_schemas
from app.utils.slug_utils import slugify
from app.utils.time_utils import utc_now
from app.services.shortlist_service import ShortlistService
from app.services.bulk_evaluation_service import (
    get_job_evaluation_progress,
    has_running_job_evaluation,
    mark_job_submissions_queued,
    queue_job_evaluation,
    recover_stale_job_evaluations,
)
from app.services import crud
from app.services.auth import ensure_job_access, get_current_recruiter
from app.services.submission_proof_service import sync_job_invite_proofs

router = APIRouter()

DEFAULT_DEEP_EVALUATION_LIMIT = 25
MAX_DEEP_EVALUATION_LIMIT = 50


def _report_refresh_needed(progress: dict) -> bool:
    evaluated_count = int(progress.get("evaluated_count") or 0)
    if evaluated_count <= 0:
        return False
    for outcome in progress.get("outcome_statuses") or []:
        expected = int(outcome.get("report_expected_candidate_count") or evaluated_count)
        if int(outcome.get("report_candidate_count") or 0) < expected:
            return True
    return False


def _ensure_job_recruiter_column(db: Session):
    columns = {column["name"] for column in inspect(db.bind).get_columns("jobs")}
    if "recruiter_id" not in columns:
        db.execute(text("ALTER TABLE jobs ADD COLUMN recruiter_id VARCHAR"))
        db.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_recruiter_id ON jobs (recruiter_id)"))
        db.commit()


@router.post("/jobs", response_model=job_schemas.JobResponse)
def create_job(
    job_data: job_schemas.JobCreate,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """Create a new job posting."""
    _ensure_job_recruiter_column(db)
    job_id = str(uuid.uuid4())
    title_slug = slugify(job_data.title)
    company_slug = slugify(job_data.company)
    slug = f"{title_slug}-{company_slug}-{job_id[:8]}"
    
    db_job = job_models.Job(
        id=job_id,
        recruiter_id=current.id,
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
def list_jobs(
    include_archived: bool = False,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """List all jobs. By default, excludes archived jobs."""
    _ensure_job_recruiter_column(db)
    query = db.query(job_models.Job).options(
        joinedload(job_models.Job.outcomes)
    )
    if current.role != "admin":
        query = query.filter(job_models.Job.recruiter_id == current.id)
    
    if not include_archived:
        query = query.filter(job_models.Job.status != "archived")
    
    jobs = query.order_by(job_models.Job.created_at.desc()).all()
    return jobs


@router.patch("/jobs/{job_id}/status")
def update_job_status(
    job_id: str,
    status_data: dict,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """Update job status (closed/archived)"""
    job = db.query(job_models.Job).filter(job_models.Job.id == job_id).first()
    ensure_job_access(job, current)
    
    new_status = status_data.get("status")
    if new_status not in ["active", "closed", "archived"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    job.status = new_status
    db.commit()
    db.refresh(job)
    
    return {"message": f"Job status updated to {new_status}", "job": job}


@router.patch("/jobs/{job_id}/archive")
def archive_job(
    job_id: str,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """Archive a job from the dashboard archive action."""
    job = db.query(job_models.Job).filter(job_models.Job.id == job_id).first()
    ensure_job_access(job, current)
    job.status = "archived"
    job.last_refreshed_at = utc_now()
    db.commit()
    db.refresh(job)
    return {"message": "Job archived successfully", "job": job}


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
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """Store evaluation results for a candidate"""
    job = db.query(job_models.Job).filter(job_models.Job.id == job_id).first()
    ensure_job_access(job, current)
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
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """
    Update candidate status (recruiter decision).
    Used when recruiter clicks 'Proceed to Interview' or 'Reject'.
    """
    job = db.query(job_models.Job).filter(job_models.Job.id == job_id).first()
    ensure_job_access(job, current)
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
def get_shortlist(
    job_id: str,
    auto_select: bool = False,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """Generate and retrieve shortlist with recommendations"""
    job = db.query(job_models.Job).filter(job_models.Job.id == job_id).first()
    ensure_job_access(job, current)
    result = ShortlistService.generate_shortlist(
        db=db,
        job_id=job_id,
        auto_select=auto_select
    )
    return result


@router.post("/jobs/{job_id}/evaluations/queue")
def queue_job_applications_for_evaluation(
    job_id: str,
    options: dict = None,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """
    Queue scalable evaluation for all submissions on a job.

    This enqueues one batch worker task for the job, not one task per
    candidate. The worker screens every queued submission cheaply, then
    optionally deep-evaluates only the top N candidates.
    """
    job = db.query(job_models.Job).filter(job_models.Job.id == job_id).first()
    ensure_job_access(job, current)

    options = options or {}
    requested_deep_limit = int(options.get("deep_limit", DEFAULT_DEEP_EVALUATION_LIMIT))
    deep_limit = max(0, min(requested_deep_limit, MAX_DEEP_EVALUATION_LIMIT))
    candidate_limit = options.get("candidate_limit")
    include_deep_evaluation = bool(options.get("include_deep_evaluation", True))
    rerun_evaluated = bool(options.get("rerun_evaluated", False))
    retry_failed_only = bool(options.get("retry_failed_only", False))

    sync_job_invite_proofs(db, job_id)
    progress = get_job_evaluation_progress(db, job_id)
    evaluating_count = max(
        int((progress.get("submission_status_counts") or {}).get("evaluating", 0) or 0),
        int((progress.get("candidate_status_counts") or {}).get("evaluating", 0) or 0),
    )

    if not progress.get("queue_active") and evaluating_count > 0:
        recover_stale_job_evaluations(db, job_id)
        progress = get_job_evaluation_progress(db, job_id)

    if has_running_job_evaluation(progress) and not rerun_evaluated:
        queued_count = mark_job_submissions_queued(
            db,
            job_id,
            retry_failed_only=retry_failed_only,
        )
        progress = get_job_evaluation_progress(db, job_id)
        report_refresh_needed = include_deep_evaluation and _report_refresh_needed(progress)
        follow_up_task_id = None
        if queued_count > 0 or report_refresh_needed:
            follow_up_task_id = queue_job_evaluation(
                job_id,
                deep_limit=max(0, deep_limit),
                candidate_limit=int(candidate_limit) if candidate_limit else None,
                include_deep_evaluation=include_deep_evaluation,
            )
            crud.create_audit_log(db, "job_evaluation", job_id, "follow_up_queued", {
                "task_id": follow_up_task_id,
                "queued_count": queued_count,
                "report_refresh_needed": report_refresh_needed,
                "deep_limit": max(0, deep_limit),
                "include_deep_evaluation": include_deep_evaluation,
            })
        return {
            "job_id": job_id,
            "task_id": follow_up_task_id,
            "queued_count": queued_count,
            "deep_limit": max(0, deep_limit),
            "include_deep_evaluation": include_deep_evaluation,
            "message": (
                "Evaluation follow-up queued to refresh reports"
                if follow_up_task_id
                else "Job evaluation is already queued or running"
            ),
            "progress": progress,
        }

    queued_count = mark_job_submissions_queued(
        db,
        job_id,
        rerun_evaluated=rerun_evaluated,
        retry_failed_only=retry_failed_only,
    )

    report_refresh_needed = include_deep_evaluation and _report_refresh_needed(progress)
    if queued_count == 0 and not report_refresh_needed and (not include_deep_evaluation or progress.get("evaluated_count", 0) == 0):
        crud.create_audit_log(db, "job_evaluation", job_id, "queue_skipped", {
            "reason": "No submissions need evaluation",
            "deep_limit": max(0, deep_limit),
            "include_deep_evaluation": include_deep_evaluation,
        })
        return {
            "job_id": job_id,
            "task_id": None,
            "queued_count": 0,
            "deep_limit": max(0, deep_limit),
            "include_deep_evaluation": include_deep_evaluation,
            "message": "No submissions need evaluation",
            "progress": get_job_evaluation_progress(db, job_id),
        }

    task_id = queue_job_evaluation(
        job_id,
        deep_limit=max(0, deep_limit),
        candidate_limit=int(candidate_limit) if candidate_limit else None,
        include_deep_evaluation=include_deep_evaluation,
    )

    crud.create_audit_log(db, "job_evaluation", job_id, "queued", {
        "task_id": task_id,
        "queued_count": queued_count,
        "deep_limit": max(0, deep_limit),
        "candidate_limit": int(candidate_limit) if candidate_limit else None,
        "include_deep_evaluation": include_deep_evaluation,
        "rerun_evaluated": rerun_evaluated,
        "retry_failed_only": retry_failed_only,
    })

    return {
        "job_id": job_id,
        "task_id": task_id,
        "queued_count": queued_count,
        "deep_limit": max(0, deep_limit),
        "include_deep_evaluation": include_deep_evaluation,
        "message": "Job evaluation queued",
        "progress": get_job_evaluation_progress(db, job_id),
    }


@router.get("/jobs/{job_id}/evaluations/progress")
def get_job_application_evaluation_progress(
    job_id: str,
    response: Response,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """Return stored progress for high-volume job evaluation."""
    job = db.query(job_models.Job).filter(job_models.Job.id == job_id).first()
    ensure_job_access(job, current)
    response.headers["Cache-Control"] = "no-store"
    return get_job_evaluation_progress(db, job_id)


@router.patch("/jobs/{job_id}/shortlist")
def update_shortlist(
    job_id: str,
    shortlist: dict,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """Manually update shortlist selection"""
    job = db.query(job_models.Job).filter(job_models.Job.id == job_id).first()
    ensure_job_access(job, current)
    result = ShortlistService.update_shortlist(
        db=db,
        job_id=job_id,
        shortlisted_candidate_ids=shortlist.get("candidate_ids", [])
    )
    return result


@router.post("/jobs/{job_id}/finalize-shortlist")
def finalize_shortlist(
    job_id: str,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """
    Finalize shortlist and close applications.
    This transitions job status to 'closed'.
    """
    job = db.query(job_models.Job).filter(job_models.Job.id == job_id).first()
    ensure_job_access(job, current)
    result = ShortlistService.finalize_shortlist(db=db, job_id=job_id)
    return result


@router.get("/jobs/{job_id}", response_model=job_schemas.JobResponse)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """Get a single job by ID."""
    job = db.query(job_models.Job).filter(job_models.Job.id == job_id).first()
    return ensure_job_access(job, current)


@router.get("/jobs/{job_id}/outcomes")
def get_job_outcomes(
    job_id: str,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """Get all outcomes for a specific job with their tasks."""
    from app.models import outcome as outcome_models
    from app.models import task as task_models
    
    job = db.query(job_models.Job).filter(job_models.Job.id == job_id).first()
    ensure_job_access(job, current)
    
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
    confirmation: str = Query("", description="Type DELETE to permanently delete a job."),
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """
    Delete or archive a job.
    - Default (soft delete): Sets status to 'archived', hides from listings
    - Hard delete: Permanently removes the job and all linked application/evaluation data
    """
    job = db.query(job_models.Job).filter(job_models.Job.id == job_id).first()
    ensure_job_access(job, current)
    
    if hard_delete:
        if confirmation != "DELETE":
            raise HTTPException(
                status_code=400,
                detail="Permanent delete requires confirmation=DELETE.",
            )

        from app.models import outcome as outcome_models
        from app.models import task as task_models
        from app.models.audit import AuditLog
        from app.models.evaluation import Evaluation
        from app.models.feedback import Feedback, SignalWeight
        from app.models.invite import Invite, InviteSubmission
        from app.models.job_candidate import JobCandidate
        from app.models.proof import Proof
        from app.models.snapshot import LLMLog

        outcome_ids = [
            row[0]
            for row in db.query(outcome_models.Outcome.id)
            .filter(outcome_models.Outcome.job_id == job_id)
            .all()
        ]
        task_ids = [
            row[0]
            for row in db.query(task_models.Task.id)
            .filter(task_models.Task.outcome_id.in_(outcome_ids))
            .all()
        ] if outcome_ids else []
        evaluation_ids = [
            row[0]
            for row in db.query(Evaluation.id)
            .filter(Evaluation.outcome_id.in_(outcome_ids))
            .all()
        ] if outcome_ids else []

        deleted_counts = {
            "feedback": 0,
            "llm_logs": 0,
            "evaluations": 0,
            "proofs": 0,
            "task_weights": 0,
            "task_weight_history": 0,
            "tasks": 0,
            "outcomes": 0,
            "invite_submissions": 0,
            "invites": 0,
            "job_candidates": 0,
            "audit_logs": 0,
        }

        if evaluation_ids:
            deleted_counts["feedback"] += db.query(Feedback).filter(
                Feedback.evaluation_id.in_(evaluation_ids)
            ).delete(synchronize_session=False)
            deleted_counts["llm_logs"] += db.query(LLMLog).filter(
                LLMLog.evaluation_id.in_(evaluation_ids)
            ).delete(synchronize_session=False)

        deleted_counts["feedback"] += db.query(Feedback).filter(
            Feedback.job_id == job_id
        ).delete(synchronize_session=False)

        if outcome_ids:
            deleted_counts["task_weight_history"] += db.query(task_models.TaskWeightHistory).filter(
                task_models.TaskWeightHistory.outcome_id.in_(outcome_ids)
            ).delete(synchronize_session=False)
            deleted_counts["evaluations"] += db.query(Evaluation).filter(
                Evaluation.outcome_id.in_(outcome_ids)
            ).delete(synchronize_session=False)
            deleted_counts["evaluations"] += db.query(Evaluation).filter(
                Evaluation.job_id.in_(outcome_ids)
            ).delete(synchronize_session=False)
            deleted_counts["proofs"] += db.query(Proof).filter(
                Proof.outcome_id.in_(outcome_ids)
            ).delete(synchronize_session=False)
            deleted_counts["tasks"] += db.query(task_models.Task).filter(
                task_models.Task.outcome_id.in_(outcome_ids)
            ).delete(synchronize_session=False)
            deleted_counts["outcomes"] += db.query(outcome_models.Outcome).filter(
                outcome_models.Outcome.id.in_(outcome_ids)
            ).delete(synchronize_session=False)
            deleted_counts["audit_logs"] += db.query(AuditLog).filter(
                AuditLog.entity_id.in_(outcome_ids)
            ).delete(synchronize_session=False)

        if task_ids:
            deleted_counts["task_weights"] += db.query(SignalWeight).filter(
                SignalWeight.task_id.in_(task_ids)
            ).delete(synchronize_session=False)

        deleted_counts["task_weight_history"] += db.query(task_models.TaskWeightHistory).filter(
            task_models.TaskWeightHistory.feedback_source_job_id == job_id
        ).delete(synchronize_session=False)
        deleted_counts["invite_submissions"] += db.query(InviteSubmission).filter(
            InviteSubmission.job_id == job_id
        ).delete(synchronize_session=False)
        deleted_counts["invites"] += db.query(Invite).filter(
            Invite.job_id == job_id
        ).delete(synchronize_session=False)
        deleted_counts["job_candidates"] += db.query(JobCandidate).filter(
            JobCandidate.job_id == job_id
        ).delete(synchronize_session=False)
        deleted_counts["audit_logs"] += db.query(AuditLog).filter(
            AuditLog.entity_id == job_id
        ).delete(synchronize_session=False)

        db.delete(job)
        db.commit()
        return {
            "message": "Job permanently deleted",
            "job_id": job_id,
            "type": "hard_delete",
            "deleted": deleted_counts,
        }
    else:
        # Soft delete - archive the job
        job.status = "archived"
        job.last_refreshed_at = utc_now()
        db.commit()
        return {"message": "Job archived successfully", "job_id": job_id, "type": "archive"}

