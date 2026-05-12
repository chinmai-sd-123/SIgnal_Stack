import logging
import json
import threading
import time
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional

import app.schemas as schemas
from app.config.database import SessionLocal
from app.models.invite import InviteSubmission
from app.models.evaluation import Evaluation
from app.models.job import Job
from app.models.job_candidate import JobCandidate
from app.models.outcome import Outcome
from app.models.proof import Proof
from app.pipeline.evaluator import Evaluator
from app.pipeline.scoring_engine import score_candidate
from app.pipeline.signal_extractor import SignalExtractor
from app.monitoring import track_evaluation_complete, track_evaluation_start
from app.services import crud
from app.services.cache import cache
from app.services.submission_proof_service import get_candidate_id, sync_job_invite_proofs
from app.services.worker_queue import TaskStatus, worker_queue
from app.utils.time_utils import utc_now

logger = logging.getLogger(__name__)

QUEUED_STATUSES = {"submitted", "queued", "failed"}
ACTIVE_STATUSES = {"queued", "evaluating"}
TERMINAL_EVALUATED_STATUSES = {"evaluated", "shortlisted", "rejected"}
DEFAULT_DEEP_REPORT_LIMIT = 25

REDIS_JOB_EVAL_QUEUE = "signalstack:job_evaluations:queue"
REDIS_JOB_EVAL_PROCESSING = "signalstack:job_evaluations:processing"
REDIS_JOB_EVAL_TASK_PREFIX = "signalstack:job_evaluations:task"

_redis_worker_thread: Optional[threading.Thread] = None
_redis_worker_running = False
_redis_worker_lock = threading.Lock()


def _redis_task_key(task_id: str) -> str:
    return f"{REDIS_JOB_EVAL_TASK_PREFIX}:{task_id}"


def _redis_available() -> bool:
    return bool(cache.redis_client)


def _set_redis_task_status(task_id: str, status: str, **extra):
    if not _redis_available():
        return
    payload = {
        "task_id": task_id,
        "status": status,
        **extra,
        "updated_at": utc_now().isoformat(),
    }
    try:
        cache.redis_client.setex(_redis_task_key(task_id), 86400, json.dumps(payload, default=str))
    except Exception as exc:
        logger.warning("Could not update Redis evaluation task status: %s", exc)


def _recover_redis_processing_queue():
    """Move tasks left in processing by a crashed worker back to pending."""
    if not _redis_available():
        return
    try:
        while True:
            item = cache.redis_client.rpop(REDIS_JOB_EVAL_PROCESSING)
            if not item:
                break
            cache.redis_client.lpush(REDIS_JOB_EVAL_QUEUE, item)
    except Exception as exc:
        logger.warning("Could not recover Redis evaluation queue: %s", exc)


def _redis_job_evaluation_worker_loop():
    logger.info("Redis job evaluation worker started")
    _recover_redis_processing_queue()

    while _redis_worker_running:
        try:
            item = cache.redis_client.brpoplpush(
                REDIS_JOB_EVAL_QUEUE,
                REDIS_JOB_EVAL_PROCESSING,
                timeout=2,
            )
            if not item:
                continue

            try:
                payload = json.loads(item)
                task_id = payload["task_id"]
                _set_redis_task_status(task_id, "running", job_id=payload.get("job_id"))
                result = evaluate_job_applications_sync(
                    payload["job_id"],
                    deep_limit=payload.get("deep_limit", 100),
                    candidate_limit=payload.get("candidate_limit"),
                    include_deep_evaluation=payload.get("include_deep_evaluation", True),
                )
                _set_redis_task_status(task_id, "completed", job_id=payload.get("job_id"), result=result)
            except Exception as exc:
                logger.exception("Redis job evaluation task failed")
                try:
                    task_id = json.loads(item).get("task_id")
                    if task_id:
                        _set_redis_task_status(task_id, "failed", error=str(exc))
                except Exception:
                    pass
            finally:
                cache.redis_client.lrem(REDIS_JOB_EVAL_PROCESSING, 1, item)
        except Exception as exc:
            logger.warning("Redis job evaluation worker error: %s", exc)

    logger.info("Redis job evaluation worker stopped")


def init_redis_job_evaluation_worker():
    """Start Redis-backed job evaluation worker when Redis is configured."""
    global _redis_worker_thread, _redis_worker_running
    if not _redis_available():
        return False

    with _redis_worker_lock:
        if _redis_worker_running and _redis_worker_thread and _redis_worker_thread.is_alive():
            return True

        _redis_worker_running = True
        _redis_worker_thread = threading.Thread(
            target=_redis_job_evaluation_worker_loop,
            name="redis-job-evaluation-worker",
            daemon=True,
        )
        _redis_worker_thread.start()
        return True


def stop_redis_job_evaluation_worker(timeout: float = 5.0):
    global _redis_worker_running
    _redis_worker_running = False
    if _redis_worker_thread and _redis_worker_thread.is_alive():
        _redis_worker_thread.join(timeout=timeout)


def get_job_evaluation_queue_backend() -> str:
    return "redis" if _redis_available() else "memory"


def _redis_payload_job_id(item: Any) -> Optional[str]:
    payload = _redis_payload(item)
    return payload.get("job_id") if payload else None


def _redis_payload(item: Any) -> Optional[Dict[str, Any]]:
    if isinstance(item, bytes):
        item = item.decode("utf-8")
    try:
        return json.loads(item)
    except Exception:
        return None


def _count_redis_job_queue_items(job_id: Optional[str]) -> int:
    if not _redis_available():
        return 0

    if not job_id:
        return int(cache.redis_client.llen(REDIS_JOB_EVAL_QUEUE) or 0) + int(
            cache.redis_client.llen(REDIS_JOB_EVAL_PROCESSING) or 0
        )

    count = 0
    for key in (REDIS_JOB_EVAL_QUEUE, REDIS_JOB_EVAL_PROCESSING):
        for item in cache.redis_client.lrange(key, 0, -1):
            if _redis_payload_job_id(item) == job_id:
                count += 1
    return count


def clear_job_evaluation_queue(job_id: str, reason: str = "completed") -> int:
    """
    Remove stale Redis queue entries for a job.

    This is intentionally conservative and is called only after the database
    says all submissions are evaluated and all outcome reports are current.
    It fixes the UI case where a duplicate Redis task keeps showing
    "Processing queue: 1" even though the report is already ready.
    """
    if not _redis_available() or not job_id:
        return 0

    removed = 0
    try:
        for key in (REDIS_JOB_EVAL_QUEUE, REDIS_JOB_EVAL_PROCESSING):
            for item in list(cache.redis_client.lrange(key, 0, -1)):
                payload = _redis_payload(item)
                if not payload or payload.get("job_id") != job_id:
                    continue

                removed += int(cache.redis_client.lrem(key, 0, item) or 0)
                task_id = payload.get("task_id")
                if task_id:
                    _set_redis_task_status(
                        task_id,
                        "skipped",
                        job_id=job_id,
                        reason=reason,
                    )
    except Exception as exc:
        logger.warning("Could not clear completed Redis evaluation queue for %s: %s", job_id, exc)
    return removed


def progress_indicates_complete(progress: Dict[str, Any]) -> bool:
    """True when no useful queue work remains for this job."""
    submissions_total = int(progress.get("submissions_total") or 0)
    evaluated_count = int(progress.get("evaluated_count") or 0)
    outcomes_total = int(progress.get("outcomes_total") or 0)
    outcomes_evaluated = int(progress.get("outcomes_evaluated") or 0)
    active_count = int(progress.get("active_count") or 0)

    if submissions_total <= 0 or evaluated_count < submissions_total or active_count > 0:
        return False
    if outcomes_total > 0 and outcomes_evaluated < outcomes_total:
        return False

    incomplete_statuses = {"applied", "submitted", "queued", "evaluating", "failed"}
    for counts_key in ("submission_status_counts", "candidate_status_counts"):
        counts = progress.get(counts_key) or {}
        if any(int(counts.get(status) or 0) > 0 for status in incomplete_statuses):
            return False

    return True


def ensure_redis_job_evaluation_worker_for_pending(job_id: Optional[str] = None) -> bool:
    """
    Wake the Redis worker when pending/processing job work exists.

    Render/Vercel-style deploys can restart the Python process while Redis still
    contains queued work. Progress polling must be able to revive the in-process
    worker; otherwise the UI can show queue: 1 forever with no evaluator active.
    """
    if not _redis_available():
        return False
    try:
        if _count_redis_job_queue_items(job_id) > 0:
            return init_redis_job_evaluation_worker()
    except Exception as exc:
        logger.warning("Could not wake Redis evaluation worker: %s", exc)
    return False


def _count_memory_job_queue_items(job_id: Optional[str]) -> int:
    if not job_id:
        return worker_queue.get_queue_size()

    task_name = f"evaluate_job:{job_id}"
    active_statuses = {TaskStatus.PENDING, TaskStatus.RUNNING}
    with worker_queue._lock:
        return sum(
            1
            for task in worker_queue.tasks.values()
            if task.name == task_name and task.status in active_statuses
        )


def get_job_evaluation_queue_size(job_id: Optional[str] = None) -> int:
    size = _count_memory_job_queue_items(job_id)
    if _redis_available():
        try:
            size += _count_redis_job_queue_items(job_id)
        except Exception as exc:
            logger.warning("Could not read Redis evaluation queue size: %s", exc)
    return size


def has_running_job_evaluation(progress: Dict[str, Any]) -> bool:
    """Return true only when a worker is actually queued/processing a job."""
    evaluating_count = max(
        int((progress.get("submission_status_counts") or {}).get("evaluating", 0) or 0),
        int((progress.get("candidate_status_counts") or {}).get("evaluating", 0) or 0),
    )
    return bool(progress.get("queue_active")) or evaluating_count > 0


def candidate_id_for_submission(submission: InviteSubmission) -> str:
    return get_candidate_id(submission)


def ensure_job_candidate(db, job_id: str, candidate_id: str, status: str = "submitted") -> JobCandidate:
    candidate = db.query(JobCandidate).filter(
        JobCandidate.job_id == job_id,
        JobCandidate.candidate_id == candidate_id,
    ).first()

    if candidate:
        if status == "queued" and candidate.status in {"applied", "submitted", "failed"}:
            candidate.status = status
        elif status == "evaluating" and candidate.status in {"applied", "submitted", "failed", "queued"}:
            candidate.status = status
        return candidate

    candidate = JobCandidate(
        id=str(uuid.uuid4()),
        job_id=job_id,
        candidate_id=candidate_id,
        status=status,
        applied_at=utc_now(),
    )
    db.add(candidate)
    return candidate


def _proof_to_schema(proof: Proof) -> schemas.ProofCreate:
    return schemas.ProofCreate(
        job_id=proof.outcome_id,
        candidate_id=proof.candidate_id,
        type=proof.type,
        payload=proof.payload_json or {},
    )


def _safe_public_signals(signals: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in (signals or {}).items() if not k.startswith("_")}


def _job_outcome_ids(db, job_id: str) -> List[str]:
    rows = db.query(Outcome.id).filter(Outcome.job_id == job_id).all()
    return [row[0] for row in rows]


def _find_submission_proof(db, submission: InviteSubmission, candidate_id: str) -> Optional[Proof]:
    """
    Find the proof linked to this exact submission, scoped to this job.

    The submission id is the strongest link. The job/outcome scope keeps the
    fallback from accidentally using a proof from another job for the same
    candidate id.
    """
    outcome_ids = _job_outcome_ids(db, submission.job_id)
    if not outcome_ids:
        return None

    candidate_proofs = db.query(Proof).filter(
        Proof.candidate_id == candidate_id,
        Proof.outcome_id.in_(outcome_ids),
    ).all()

    return next(
        (
            item for item in candidate_proofs
            if (item.payload_json or {}).get("invite_submission_id") == submission.id
        ),
        candidate_proofs[0] if candidate_proofs else None,
    )


def _verification_status(signals: Dict[str, Any], risk_flags: List[str]) -> str:
    if "fork_unmodified" in risk_flags:
        return "conflict"
    if "authorship_fraction" not in signals:
        return "unverified"

    value = signals.get("authorship_fraction", 0.0)
    if isinstance(value, dict):
        value = value.get("value", 0.0)
    authorship = float(value or 0.0)
    if authorship >= 0.2:
        return "verified"
    if authorship < 0.05:
        return "conflict"
    return "unverified"


def _production_readiness(signals: Dict[str, Any]) -> float:
    keys = {
        "tests_present": 0.25,
        "ci_cd_present": 0.15,
        "deployment_ready": 0.15,
        "dockerfile_present": 0.10,
        "readme_quality_score": 0.15,
        "rate_limiting_present": 0.10,
        "migrations_present": 0.10,
    }
    score = 0.0
    for key, weight in keys.items():
        value = signals.get(key, 0.0)
        if isinstance(value, dict):
            value = value.get("value", 0.0)
        score += min(max(float(value or 0.0), 0.0), 1.0) * weight
    return round(score / sum(keys.values()), 3)


def _submission_payload_summary(submission: InviteSubmission) -> Dict[str, Any]:
    return {
        "submission_id": submission.id,
        "candidate_name": submission.candidate_name,
        "candidate_email": submission.candidate_email,
        "github_username": submission.github_username,
        "repo_url": submission.repo_url,
        "resume_url": submission.resume_url,
    }


def _evaluated_candidate_rows(db, job_id: str, deep_limit: int) -> List[JobCandidate]:
    valid_candidate_ids = _candidate_ids_for_job_submissions(db, job_id)
    query = db.query(JobCandidate).filter(
        JobCandidate.job_id == job_id,
        JobCandidate.evaluation_score.isnot(None),
    )
    if valid_candidate_ids:
        query = query.filter(JobCandidate.candidate_id.in_(valid_candidate_ids))
    query = query.order_by(JobCandidate.evaluation_score.desc())

    if deep_limit > 0:
        query = query.limit(deep_limit)

    return query.all()


def _candidate_ids_for_job_submissions(db, job_id: str) -> set[str]:
    submissions = db.query(InviteSubmission).filter(InviteSubmission.job_id == job_id).all()
    return {candidate_id_for_submission(submission) for submission in submissions}


def _submission_needs_candidate_evaluation(db, submission: InviteSubmission) -> bool:
    candidate_id = candidate_id_for_submission(submission)
    candidate = db.query(JobCandidate).filter(
        JobCandidate.job_id == submission.job_id,
        JobCandidate.candidate_id == candidate_id,
    ).first()
    return not candidate or candidate.evaluation_score is None


def _signals_from_candidate(candidate: JobCandidate) -> Dict[str, Any]:
    data = candidate.evaluation_data or {}
    return data.get("signals") or {}


def _candidate_ids_for_deep_evaluation(
    db,
    job_id: str,
    deep_limit: int,
    signals_by_candidate: Dict[str, Dict[str, Any]],
) -> List[str]:
    evaluated_candidates = _evaluated_candidate_rows(db, job_id, max(0, deep_limit))
    for candidate in evaluated_candidates:
        signals_by_candidate.setdefault(candidate.candidate_id, _signals_from_candidate(candidate))
    return [candidate.candidate_id for candidate in evaluated_candidates]


def _average_summary_dimensions(candidate_summaries: List[schemas.CandidateSummary]) -> Optional[Dict[str, float]]:
    totals: Dict[str, float] = {}
    count = 0
    for summary in candidate_summaries:
        if not summary.dimensions:
            continue
        count += 1
        for key, value in summary.dimensions.items():
            try:
                totals[key] = totals.get(key, 0.0) + float(value or 0.0)
            except (TypeError, ValueError):
                totals[key] = totals.get(key, 0.0)
    if count <= 0:
        return None
    return {key: round(value / count, 2) for key, value in totals.items()}


def _latest_evaluation_for_outcome(db, outcome_id: str) -> Optional[Evaluation]:
    return db.query(Evaluation).filter(
        Evaluation.outcome_id == outcome_id,
        Evaluation.status == "completed",
    ).order_by(Evaluation.created_at.desc()).first()


def _evaluation_from_payload(payload: Dict[str, Any]) -> Optional[schemas.EvaluationResponse]:
    if not payload:
        return None
    try:
        return schemas.EvaluationResponse.model_validate(payload)
    except Exception as exc:
        logger.warning("Could not parse existing evaluation payload for incremental merge: %s", exc)
        return None


def _merge_candidate_summaries(
    existing: List[schemas.CandidateSummary],
    delta: List[schemas.CandidateSummary],
) -> List[schemas.CandidateSummary]:
    by_candidate = {item.candidate_id: item for item in existing}
    for item in delta:
        by_candidate[item.candidate_id] = item

    merged = list(by_candidate.values())
    merged.sort(key=lambda item: item.overall_score or 0.0, reverse=True)
    return merged


def _merge_allocation(
    existing: schemas.WorkAllocation,
    delta: Optional[schemas.WorkAllocation],
) -> schemas.WorkAllocation:
    if not delta:
        return existing

    scores = {item.candidate_id: item for item in existing.top_candidates or []}
    for item in delta.top_candidates or []:
        scores[item.candidate_id] = item

    ranked_scores = sorted(scores.values(), key=lambda item: item.score or 0.0, reverse=True)
    best = ranked_scores[0] if ranked_scores else None

    return schemas.WorkAllocation(
        task_id=existing.task_id,
        task_title=existing.task_title,
        recommended_candidate=best.candidate_id if best else "None",
        confidence=round(best.score, 2) if best else 0.0,
        reasons=[best.justification] if best and best.justification else existing.reasons,
        evidence=best.evidence if best and best.evidence else existing.evidence,
        top_candidates=ranked_scores,
    )


def _merge_evaluation_response(
    existing: schemas.EvaluationResponse,
    delta: schemas.EvaluationResponse,
) -> schemas.EvaluationResponse:
    delta_by_task = {
        allocation.task_id or allocation.task_title: allocation
        for allocation in delta.work_allocation or []
    }
    merged_allocations = [
        _merge_allocation(
            allocation,
            delta_by_task.get(allocation.task_id or allocation.task_title),
        )
        for allocation in existing.work_allocation or []
    ]

    existing_keys = {allocation.task_id or allocation.task_title for allocation in existing.work_allocation or []}
    for allocation in delta.work_allocation or []:
        key = allocation.task_id or allocation.task_title
        if key not in existing_keys:
            merged_allocations.append(allocation)

    merged_summaries = _merge_candidate_summaries(
        list(existing.candidate_summaries or []),
        list(delta.candidate_summaries or []),
    )

    wins = defaultdict(int)
    for allocation in merged_allocations:
        if allocation.recommended_candidate and allocation.recommended_candidate != "None":
            wins[allocation.recommended_candidate] += 1

    for summary in merged_summaries:
        summary.tasks_won = wins.get(summary.candidate_id, 0)

    top_summary = merged_summaries[0] if merged_summaries else None
    global_signals_used = sorted(set(existing.global_signals_used or []) | set(delta.global_signals_used or []))
    risk_flags = sorted(set((top_summary.risk_flags if top_summary else []) or []))

    return schemas.EvaluationResponse(
        job_id=existing.job_id,
        job_title=existing.job_title or delta.job_title,
        fit_score=round(top_summary.overall_score, 2) if top_summary else 0.0,
        capability_score=top_summary.capability_score if top_summary else None,
        evidence_confidence=top_summary.evidence_confidence if top_summary else None,
        production_readiness=top_summary.production_readiness if top_summary else None,
        verification_status=top_summary.verification_status if top_summary else "unverified",
        work_allocation=merged_allocations,
        global_signals_used=global_signals_used,
        risk_flags=risk_flags,
        human_action_required=True,
        dimensions=_average_summary_dimensions(merged_summaries),
        candidate_summaries=merged_summaries,
    )


def _mark_failure(db, candidate: JobCandidate, submission: Optional[InviteSubmission], error: str):
    candidate.status = "failed"
    candidate.evaluation_data = {
        **(candidate.evaluation_data or {}),
        "stage": "failed",
        "error": error[:1000],
        "failed_at": utc_now().isoformat(),
    }
    if submission:
        submission.status = "failed"
    db.commit()


def _recover_interrupted_evaluations(db, job_id: str) -> int:
    """
    If the process died while a Redis task was processing, DB rows can be left
    in evaluating even though no worker owns them anymore. Move those rows back
    to queued before a recovered task runs.
    """
    recovered = 0

    submissions = db.query(InviteSubmission).filter(
        InviteSubmission.job_id == job_id,
        InviteSubmission.status == "evaluating",
    ).all()
    for submission in submissions:
        submission.status = "queued"
        recovered += 1

    candidates = db.query(JobCandidate).filter(
        JobCandidate.job_id == job_id,
        JobCandidate.status == "evaluating",
        JobCandidate.evaluation_score.is_(None),
    ).all()
    for candidate in candidates:
        candidate.status = "queued"
        candidate.evaluation_data = {
            **(candidate.evaluation_data or {}),
            "stage": "queued",
            "recovered_at": utc_now().isoformat(),
        }

    if recovered or candidates:
        db.commit()

    return recovered


def recover_stale_job_evaluations(db, job_id: str) -> int:
    """Public wrapper used by API routes before deciding whether to enqueue."""
    return _recover_interrupted_evaluations(db, job_id)


def _screen_submission(db, submission: InviteSubmission, extractor: SignalExtractor) -> Dict[str, Any]:
    candidate_id = candidate_id_for_submission(submission)
    candidate = ensure_job_candidate(db, submission.job_id, candidate_id, status="evaluating")
    submission.status = "evaluating"
    db.commit()

    proof = _find_submission_proof(db, submission, candidate_id)

    if not proof:
        _mark_failure(db, candidate, submission, "No proof record found for submission.")
        return {"candidate_id": candidate_id, "status": "failed", "score": 0.0}

    proof_schema = _proof_to_schema(proof)
    signals = extractor.extract_signals(proof_schema)
    public_signals = _safe_public_signals(signals)
    scoring = score_candidate(public_signals)

    verification = _verification_status(public_signals, scoring.risk_flags)
    score = round(scoring.capped_score * 100, 2)
    now = utc_now().isoformat()

    candidate.status = "evaluated"
    candidate.evaluation_score = score
    candidate.outcome_coverage = round(scoring.confidence * 100, 2)
    candidate.evaluated_at = utc_now()
    candidate.evaluation_data = {
        "stage": "screened",
        "screened_at": now,
        "screening": {
            "score": score,
            "raw_score": scoring.raw_score,
            "normalized_score": scoring.normalized_score,
            "capped_score": scoring.capped_score,
            "evidence_confidence": scoring.confidence,
            "production_readiness": _production_readiness(public_signals),
            "verification_status": verification,
            "risk_flags": scoring.risk_flags,
        },
        "signals": public_signals,
        "submission": _submission_payload_summary(submission),
    }
    submission.status = "evaluated"
    db.commit()

    return {
        "candidate_id": candidate_id,
        "status": "evaluated",
        "score": score,
        "signals": signals,
    }


def _queued_submissions(db, job_id: str, candidate_limit: Optional[int] = None) -> List[InviteSubmission]:
    query = db.query(InviteSubmission).filter(
        InviteSubmission.job_id == job_id,
        InviteSubmission.status.in_(list(QUEUED_STATUSES)),
    ).order_by(InviteSubmission.submitted_at.asc())

    if candidate_limit:
        query = query.limit(candidate_limit)

    return query.all()


def _deep_evaluate_top_candidates(
    db,
    job_id: str,
    candidate_ids: List[str],
    signals_by_candidate: Dict[str, Dict[str, Any]],
) -> int:
    if not candidate_ids:
        return 0

    outcomes = db.query(Outcome).filter(Outcome.job_id == job_id).all()
    evaluator = Evaluator()
    deep_scores = defaultdict(list)
    deep_payloads = defaultdict(list)
    evaluations_created = 0

    for outcome in outcomes:
        outcome_id = outcome.id
        outcome_title = outcome.title
        latest = _latest_evaluation_for_outcome(db, outcome_id)
        existing_response = _evaluation_from_payload(latest.evaluation_json) if latest else None
        existing_candidate_ids = {
            item.candidate_id
            for item in (existing_response.candidate_summaries if existing_response else [])
            if item.candidate_id
        }
        expected_candidate_ids = set(candidate_ids)
        missing_candidate_ids = expected_candidate_ids - existing_candidate_ids
        candidate_ids_to_evaluate = (
            [candidate_id for candidate_id in candidate_ids if candidate_id in missing_candidate_ids]
            if existing_response
            else list(candidate_ids)
        )

        if existing_response and not candidate_ids_to_evaluate:
            continue

        proofs = db.query(Proof).filter(
            Proof.outcome_id == outcome_id,
            Proof.candidate_id.in_(candidate_ids_to_evaluate),
        ).all()
        if not proofs:
            continue

        outcome_schema = schemas.OutcomeResponse.model_validate(outcome)
        proof_schemas = [_proof_to_schema(proof) for proof in proofs]
        signals_map = {
            candidate_id: signals_by_candidate.get(candidate_id, {})
            for candidate_id in candidate_ids
        }
        db.rollback()

        if hasattr(evaluator, "evaluate_batched"):
            delta_evaluation = evaluator.evaluate_batched(outcome_schema, proof_schemas, signals_map)
        else:
            delta_evaluation = evaluator.evaluate(outcome_schema, proof_schemas, signals_map)

        evaluation = (
            _merge_evaluation_response(existing_response, delta_evaluation)
            if existing_response
            else delta_evaluation
        )
        db.rollback()
        crud.create_evaluation(db, evaluation)
        evaluations_created += 1

        for summary in evaluation.candidate_summaries:
            deep_scores[summary.candidate_id].append(summary.overall_score)
            deep_payloads[summary.candidate_id].append({
                "outcome_id": outcome_id,
                "outcome_title": outcome_title,
                "overall_score": summary.overall_score,
                "capability_score": summary.capability_score,
                "evidence_confidence": summary.evidence_confidence,
                "production_readiness": summary.production_readiness,
                "verification_status": summary.verification_status,
                "risk_flags": summary.risk_flags,
            })

    for candidate_id, scores in deep_scores.items():
        candidate = db.query(JobCandidate).filter(
            JobCandidate.job_id == job_id,
            JobCandidate.candidate_id == candidate_id,
        ).first()
        if not candidate or not scores:
            continue

        deep_score = round((sum(scores) / len(scores)) * 100, 2)
        existing = candidate.evaluation_data or {}
        candidate.evaluation_score = deep_score
        candidate.evaluated_at = utc_now()
        candidate.evaluation_data = {
            **existing,
            "stage": "deep_evaluated",
            "deep_evaluated_at": utc_now().isoformat(),
            "deep_evaluation": {
                "score": deep_score,
                "outcomes": deep_payloads[candidate_id],
            },
        }

    db.commit()
    return evaluations_created


def evaluate_job_applications_sync(
    job_id: str,
    deep_limit: int = 25,
    candidate_limit: Optional[int] = None,
    include_deep_evaluation: bool = True,
) -> Dict[str, Any]:
    """Screen all submissions for a job, then deep-evaluate only the top N."""
    started_at = time.perf_counter()
    track_evaluation_start()
    success = False
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        sync_job_invite_proofs(db, job_id)
        _recover_interrupted_evaluations(db, job_id)

        extractor = SignalExtractor()
        screened: List[Dict[str, Any]] = []
        signals_by_candidate: Dict[str, Dict[str, Any]] = {}

        evaluations_created = 0
        deep_evaluated_candidates = 0
        remaining_candidate_limit = candidate_limit
        max_cycles = 1 if candidate_limit else 3

        for cycle in range(max_cycles):
            submissions = _queued_submissions(db, job_id, remaining_candidate_limit)

            if not submissions and cycle > 0:
                break

            for submission in submissions:
                candidate_id = candidate_id_for_submission(submission)
                try:
                    result = _screen_submission(db, submission, extractor)
                    screened.append(result)
                    if result.get("signals"):
                        signals_by_candidate[candidate_id] = result["signals"]
                except Exception as exc:
                    logger.exception("Failed to screen submission %s", submission.id)
                    candidate = ensure_job_candidate(db, job_id, candidate_id, status="failed")
                    _mark_failure(db, candidate, submission, str(exc))
                    screened.append({"candidate_id": candidate_id, "status": "failed", "score": 0.0})

            if remaining_candidate_limit is not None:
                remaining_candidate_limit = max(0, remaining_candidate_limit - len(submissions))

            top_candidate_ids = _candidate_ids_for_deep_evaluation(
                db,
                job_id,
                deep_limit,
                signals_by_candidate,
            )
            deep_evaluated_candidates = len(top_candidate_ids)

            if include_deep_evaluation and top_candidate_ids and deep_limit > 0:
                sync_job_invite_proofs(db, job_id)
                evaluations_created += _deep_evaluate_top_candidates(
                    db,
                    job_id,
                    top_candidate_ids,
                    signals_by_candidate,
                )

            if remaining_candidate_limit == 0:
                break

            if not _queued_submissions(db, job_id, 1):
                break

        successful = [row for row in screened if row.get("status") == "evaluated"]

        success = True
        return {
            "job_id": job_id,
            "screened": len(screened),
            "evaluated": len(successful),
            "failed": len([row for row in screened if row.get("status") == "failed"]),
            "deep_evaluated_candidates": deep_evaluated_candidates if include_deep_evaluation else 0,
            "evaluations_created": evaluations_created,
        }
    finally:
        track_evaluation_complete(time.perf_counter() - started_at, success=success)
        db.close()


def queue_job_evaluation(
    job_id: str,
    deep_limit: int = 25,
    candidate_limit: Optional[int] = None,
    include_deep_evaluation: bool = True,
) -> str:
    if _redis_available():
        init_redis_job_evaluation_worker()
        task_id = str(uuid.uuid4())[:8]
        payload = {
            "task_id": task_id,
            "job_id": job_id,
            "deep_limit": deep_limit,
            "candidate_limit": candidate_limit,
            "include_deep_evaluation": include_deep_evaluation,
            "created_at": utc_now().isoformat(),
        }
        _set_redis_task_status(task_id, "pending", job_id=job_id)
        cache.redis_client.lpush(REDIS_JOB_EVAL_QUEUE, json.dumps(payload))
        return task_id

    return worker_queue.enqueue(
        evaluate_job_applications_sync,
        job_id,
        deep_limit=deep_limit,
        candidate_limit=candidate_limit,
        include_deep_evaluation=include_deep_evaluation,
        name=f"evaluate_job:{job_id}",
        priority=5,
    )


def mark_job_submissions_queued(
    db,
    job_id: str,
    rerun_evaluated: bool = False,
    retry_failed_only: bool = False,
) -> int:
    statuses = ["failed"] if retry_failed_only else list(QUEUED_STATUSES)
    if rerun_evaluated:
        statuses.extend(TERMINAL_EVALUATED_STATUSES)

    submissions = db.query(InviteSubmission).filter(
        InviteSubmission.job_id == job_id,
        InviteSubmission.status.in_(statuses),
    ).all()
    if not rerun_evaluated and not retry_failed_only:
        evaluated_submissions = db.query(InviteSubmission).filter(
            InviteSubmission.job_id == job_id,
            InviteSubmission.status.in_(list(TERMINAL_EVALUATED_STATUSES)),
        ).all()
        submissions.extend(
            submission
            for submission in evaluated_submissions
            if _submission_needs_candidate_evaluation(db, submission)
        )

    for submission in submissions:
        submission.status = "queued"
        candidate_id = candidate_id_for_submission(submission)
        candidate = ensure_job_candidate(db, job_id, candidate_id, status="queued")
        candidate.evaluation_data = {
            **(candidate.evaluation_data or {}),
            "stage": "queued",
            "queued_at": utc_now().isoformat(),
        }

    db.commit()
    return len(submissions)


def get_job_evaluation_progress(db, job_id: str) -> Dict[str, Any]:
    submissions = db.query(InviteSubmission).filter(InviteSubmission.job_id == job_id).all()
    valid_candidate_ids = {candidate_id_for_submission(submission) for submission in submissions}
    candidate_query = db.query(JobCandidate).filter(JobCandidate.job_id == job_id)
    if valid_candidate_ids:
        candidate_query = candidate_query.filter(JobCandidate.candidate_id.in_(valid_candidate_ids))
    candidates = candidate_query.all()
    outcomes = db.query(Outcome).filter(Outcome.job_id == job_id).all()
    outcome_ids = [outcome.id for outcome in outcomes]

    submission_counts: Dict[str, int] = defaultdict(int)
    for submission in submissions:
        submission_counts[submission.status or "submitted"] += 1

    candidate_counts: Dict[str, int] = defaultdict(int)
    for candidate in candidates:
        candidate_counts[candidate.status or "submitted"] += 1

    evaluated = [c for c in candidates if c.evaluation_score is not None]
    evaluated.sort(key=lambda c: c.evaluation_score or 0.0, reverse=True)
    expected_report_candidates = evaluated[:DEFAULT_DEEP_REPORT_LIMIT]
    evaluated_candidate_ids = {c.candidate_id for c in expected_report_candidates}

    evaluations = []
    if outcome_ids:
        evaluations = db.query(Evaluation).filter(Evaluation.outcome_id.in_(outcome_ids)).all()
    latest_evaluation_by_outcome: Dict[str, Evaluation] = {}
    for item in evaluations:
        if not item.evaluation_json:
            continue
        current = latest_evaluation_by_outcome.get(item.outcome_id)
        if not current or (item.created_at or utc_now()) > (current.created_at or utc_now()):
            latest_evaluation_by_outcome[item.outcome_id] = item

    outcome_statuses = []
    outcomes_ready = 0
    for outcome in outcomes:
        latest_evaluation = latest_evaluation_by_outcome.get(outcome.id)
        latest_payload = latest_evaluation.evaluation_json if latest_evaluation else {}
        report_candidate_ids = {
            item.get("candidate_id")
            for item in (latest_payload or {}).get("candidate_summaries", [])
            if item.get("candidate_id")
        }
        expected_candidate_ids = set(evaluated_candidate_ids)
        missing_candidate_count = len(expected_candidate_ids - report_candidate_ids)
        has_report = bool(latest_evaluation)
        is_ready = has_report and missing_candidate_count == 0
        if is_ready:
            outcomes_ready += 1

        outcome_statuses.append({
            "outcome_id": outcome.id,
            "title": outcome.title,
            "status": "evaluated" if is_ready else ("stale" if has_report and expected_candidate_ids else "pending"),
            "latest_evaluation_id": latest_evaluation.id if latest_evaluation else None,
            "latest_evaluated_at": latest_evaluation.created_at.isoformat()
            if latest_evaluation and latest_evaluation.created_at else None,
            "report_candidate_count": len(report_candidate_ids),
            "report_expected_candidate_count": len(expected_candidate_ids),
            "report_missing_candidate_count": missing_candidate_count,
        })

    progress_core = {
        "submissions_total": len(submissions),
        "candidates_total": len(candidates),
        "outcomes_total": len(outcomes),
        "outcomes_evaluated": outcomes_ready,
        "outcome_statuses": outcome_statuses,
        "submission_status_counts": dict(sorted(submission_counts.items())),
        "candidate_status_counts": dict(sorted(candidate_counts.items())),
        "active_count": sum(candidate_counts.get(status, 0) for status in ACTIVE_STATUSES),
        "evaluated_count": len(evaluated),
    }

    queue_cleanup_count = 0
    if progress_indicates_complete(progress_core):
        queue_cleanup_count = clear_job_evaluation_queue(job_id, reason="job_complete")
    else:
        ensure_redis_job_evaluation_worker_for_pending(job_id)

    job_queue_size = get_job_evaluation_queue_size(job_id)

    return {
        "job_id": job_id,
        **progress_core,
        "top_candidates": [
            {
                "candidate_id": c.candidate_id,
                "candidate_name": ((c.evaluation_data or {}).get("submission") or {}).get("candidate_name"),
                "candidate_email": ((c.evaluation_data or {}).get("submission") or {}).get("candidate_email"),
                "repo_url": ((c.evaluation_data or {}).get("submission") or {}).get("repo_url"),
                "status": c.status,
                "score": c.evaluation_score,
                "coverage": c.outcome_coverage,
                "stage": (c.evaluation_data or {}).get("stage"),
                "verification_status": (
                    (c.evaluation_data or {}).get("screening", {}).get("verification_status")
                    or (c.evaluation_data or {}).get("deep_evaluation", {}).get("verification_status")
                ),
                "risk_flags": (c.evaluation_data or {}).get("screening", {}).get("risk_flags", []),
            }
            for c in evaluated[:20]
        ],
        "queue_size": job_queue_size,
        "queue_active": job_queue_size > 0,
        "global_queue_size": get_job_evaluation_queue_size(),
        "queue_backend": get_job_evaluation_queue_backend(),
        "queue_cleanup_count": queue_cleanup_count,
    }
