from sqlalchemy.orm import Session
from sqlalchemy import desc
import app.models as models
import app.schemas as schemas
import json
import uuid

def get_outcome(db: Session, outcome_id: str):
    return db.query(models.Outcome).filter(models.Outcome.id == outcome_id).first()

def get_outcome_by_slug(db: Session, slug: str):
    return db.query(models.Outcome).filter(models.Outcome.slug == slug).first()

def get_outcomes(db: Session, category: str = None):
    query = db.query(models.Outcome)
    if category:
        # Simple case-insensitive match or exact match. 
        # User URLs are slugs "software-engineering". stored category is "Software Engineering".
        # We need a mapping or flexible search. 
        # For MVP, let's assume we pass the exact string or handle it. 
        # Actually, let's filter by ILIKE for flexibility
        query = query.filter(models.Outcome.category.ilike(f"%{category.replace('-', ' ')}%"))
    return query.all()

def create_outcome(db: Session, outcome: schemas.OutcomeCreate, job_id: str = None, **kwargs) -> models.Outcome:
    # Check if is_template request
    is_template = getattr(outcome, "is_template", 0)
    
    db_outcome = models.Outcome(
        id=str(uuid.uuid4()),
        job_id=job_id,
        title=outcome.title,
        description=outcome.description,
        is_template=is_template,
        source_template_id=getattr(outcome, "source_template_id", None),
        **kwargs
    )
    db.add(db_outcome)
    db.commit()
    db.refresh(db_outcome)

    for task in outcome.tasks:
        db_task = models.Task(
            id=str(uuid.uuid4()),
            outcome_id=db_outcome.id,
            name=task.name,
            priority=task.priority,
            weight=task.weight,
            version=1
        )
        db.add(db_task)
    
    db.commit()
    return db_outcome

def update_outcome(db: Session, outcome_id: str, payload: schemas.OutcomeUpdate) -> models.Outcome:
    db_outcome = get_outcome(db, outcome_id)
    if not db_outcome:
        return None

    data = payload.model_dump(exclude_unset=True, exclude={"tasks"})
    tasks = payload.tasks if "tasks" in payload.model_fields_set else None

    for field, value in data.items():
        if value is not None and hasattr(db_outcome, field):
            setattr(db_outcome, field, value)

    if tasks is not None:
        db.query(models.Task).filter(models.Task.outcome_id == outcome_id).delete(synchronize_session=False)
        priority_map = {"High": 3, "Medium": 2, "Low": 1}
        total_score = sum(priority_map.get(task.priority, 1) for task in tasks)
        current_weight_sum = 0.0

        for index, task in enumerate(tasks):
            if total_score > 0:
                weight = priority_map.get(task.priority, 1) / total_score
            else:
                weight = task.weight or 0.0

            if index == len(tasks) - 1:
                weight = max(0.0, 1.0 - current_weight_sum)
            else:
                weight = round(weight, 4)
                current_weight_sum += weight

            db.add(models.Task(
                id=str(uuid.uuid4()),
                outcome_id=outcome_id,
                name=task.name,
                priority=task.priority,
                weight=weight,
                version=(db_outcome.version or 1) + 1,
            ))

    db_outcome.version = (db_outcome.version or 1) + 1
    db.query(models.Evaluation).filter(models.Evaluation.outcome_id == outcome_id).delete(synchronize_session=False)
    db.commit()
    db.refresh(db_outcome)
    return db_outcome

def delete_outcome(db: Session, outcome_id: str) -> bool:
    db_outcome = get_outcome(db, outcome_id)
    if not db_outcome:
        return False

    db.query(models.Evaluation).filter(models.Evaluation.outcome_id == outcome_id).delete(synchronize_session=False)
    db.query(models.Evaluation).filter(models.Evaluation.job_id == outcome_id).delete(synchronize_session=False)
    db.query(models.Proof).filter(models.Proof.outcome_id == outcome_id).delete(synchronize_session=False)
    db.delete(db_outcome)
    db.commit()
    return True

def instantiate_outcome_from_template(db: Session, template_id: str, target_job_id: str) -> models.Outcome:
    """
    Creates a new Outcome instance from a Master Template.
    Deep copies the outcome and all its trained tasks.
    """
    template = db.query(models.Outcome).filter(models.Outcome.id == template_id).first()
    if not template:
        raise ValueError("Template not found")

    # CRITICAL: Refresh to ensure we have the absolute latest weights if they were just updated
    db.refresh(template)

    # 1. Clone Outcome
    new_outcome = models.Outcome(
        id=str(uuid.uuid4()),
        job_id=target_job_id,
        title=template.title,
        description=template.description,
        is_template=0,  # Instance
        source_template_id=template.id,  # Link back to master
        # Copy other fields as needed
        proof_type=template.proof_type
    )
    db.add(new_outcome)
    db.flush() # Generate ID

    # 2. Clone Tasks (Preserving Weights!)
    # We query tasks DIRECTLY to ensure we get the fresh weights from DB, ignoring any relationship caching
    template_tasks = db.query(models.Task).filter(models.Task.outcome_id == template_id).all()
    
    for task in template_tasks:
        new_task = models.Task(
            id=str(uuid.uuid4()),
            outcome_id=new_outcome.id,
            name=task.name,
            priority=task.priority,
            weight=task.weight, # INHERIT THE LATEST "TRAINED" WEIGHT
            version=1
        )
        db.add(new_task)

    db.commit()
    return new_outcome

def get_outcome_templates(db: Session):
    return db.query(models.Outcome).filter(models.Outcome.is_template == 1).order_by(desc(models.Outcome.created_at)).all()

def create_tasks_batch(db: Session, batch: schemas.TaskBatchCreate):
    # 1. Calculate Weights
    # Ratios: High=3, Medium=2, Low=1
    priority_map = {"High": 3, "Medium": 2, "Low": 1}
    
    total_score = 0
    for task in batch.tasks:
        p_score = priority_map.get(task.priority, 1) # Default to Low if unknown
        total_score += p_score
        
    tasks_db = []
    current_weight_sum = 0
    
    for i, task in enumerate(batch.tasks):
        p_score = priority_map.get(task.priority, 1)
        
        # Calculate weight
        if total_score > 0:
            weight = p_score / total_score
        else:
            weight = 0 # Should not happen if tasks > 0
            
        # Adjust last task to ensure exact 1.0 sum (handle floating point drift)
        if i == len(batch.tasks) - 1:
            weight = 1.0 - current_weight_sum
            # Safety check: if weight became negative or weird due to drift (unlikely with this logic but good practice)
            if weight < 0: weight = 0
        else:
            # Round to 4 decimal places for cleanliness, but keep track of sum
            weight = round(weight, 4)
            current_weight_sum += weight
            
        new_task = models.Task(
            id=str(uuid.uuid4()),
            outcome_id=batch.outcome_id,
            name=task.name,
            priority=task.priority,
            weight=weight,
            version=1
        )
        tasks_db.append(new_task)
        
    db.add_all(tasks_db)
    db.commit()
    
    # Refresh logic not easy with add_all, but we can query them back or just return the inputs
    return tasks_db

def create_proof(db: Session, proof: schemas.ProofCreate):
    db_proof = models.Proof(
        outcome_id=proof.job_id,
        candidate_id=proof.candidate_id,
        type=proof.type,
        payload_json=proof.payload
    )
    db.add(db_proof)
    db.commit()
    db.refresh(db_proof)
    # Return schema
    return proof

def get_proofs(db: Session, outcome_id: str):
    return db.query(models.Proof).filter(models.Proof.outcome_id == outcome_id).all()

def create_evaluation(db: Session, evaluation: schemas.EvaluationResponse):
    db_eval = models.Evaluation(
        job_id=evaluation.job_id,
        outcome_id=evaluation.job_id,
        evaluation_json=evaluation.model_dump(),
        fit_score=evaluation.fit_score
    )
    db.add(db_eval)
    db.commit()
    db.refresh(db_eval)
    return db_eval

def get_evaluations(db: Session):
    return db.query(models.Evaluation).order_by(desc(models.Evaluation.created_at)).all()

def get_evaluation_summaries(db: Session):
    # Join Evaluation and Outcome to get the title
    results = db.query(models.Evaluation, models.Outcome).join(models.Outcome, models.Evaluation.outcome_id == models.Outcome.id).order_by(desc(models.Evaluation.created_at)).all()
    
    summaries = []
    for eval_model, outcome_model in results:
        eval_data = eval_model.evaluation_json
        summaries.append({
            "job_id": eval_model.job_id,
            "outcome_title": outcome_model.title,
            "fit_score": eval_model.fit_score,
            "human_action_required": eval_data.get("human_action_required", True),
            "risk_flags": eval_data.get("risk_flags", []),
            "created_at": eval_model.created_at
        })
    return summaries

def get_signal_weights(db: Session):
    return db.query(models.SignalWeight).all()

def update_signal_weight(db: Session, signal_name: str, weight: float, task_id: str = None):
    # Check if exists
    query = db.query(models.SignalWeight).filter(models.SignalWeight.signal_name == signal_name)
    if task_id:
        query = query.filter(models.SignalWeight.task_id == task_id)
    
    db_weight = query.first()
    if db_weight:
        db_weight.weight = weight
    else:
        db_weight = models.SignalWeight(signal_name=signal_name, weight=weight, task_id=task_id)
        db.add(db_weight)
    db.commit()
    return db_weight

def mark_evaluation_complete(db: Session, job_id: str, decision_metrics: dict):
    # Update the LATEST evaluation for this job (not an old one)
    db_eval = db.query(models.Evaluation).filter(
        models.Evaluation.job_id == job_id
    ).order_by(desc(models.Evaluation.created_at)).first()
    
    if db_eval:
        data = dict(db_eval.evaluation_json)
        data['human_action_required'] = False
        data['decision'] = decision_metrics # Store what we decided
        db_eval.evaluation_json = data
        db.add(db_eval) # Flag as modified

        # Sync status to InviteSubmissions
        selected = set(decision_metrics.get("selected_candidates", []))
        if decision_metrics.get("selected_candidate"):
            selected.add(decision_metrics["selected_candidate"])
        rejected = set(decision_metrics.get("rejected_candidates", []))
        
        # Get proofs for this outcome to map candidate_id to invite_submission_id
        proofs = db.query(models.Proof).filter(models.Proof.outcome_id == job_id).all()
        for proof in proofs:
            sub_id = proof.payload_json.get("invite_submission_id") if proof.payload_json else None
            if sub_id:
                sub = db.query(models.InviteSubmission).filter(models.InviteSubmission.id == sub_id).first()
                if sub:
                    if proof.candidate_id in selected:
                        sub.status = "hired"
                    elif proof.candidate_id in rejected or decision_metrics.get("action_taken") == "reject_all":
                        sub.status = "rejected"
                    db.add(sub)

        db.commit()
        db.refresh(db_eval)
        return db_eval
    return None

def reset_evaluation_decision(db: Session, job_id: str):
    """Reset the hiring decision for a job, allowing a new decision to be made."""
    db_eval = db.query(models.Evaluation).filter(
        models.Evaluation.job_id == job_id
    ).order_by(desc(models.Evaluation.created_at)).first()
    
    if db_eval:
        data = dict(db_eval.evaluation_json)
        data['human_action_required'] = True
        data['decision'] = None  # Clear the decision
        db_eval.evaluation_json = data
        db.add(db_eval)

        # Reset InviteSubmissions status
        proofs = db.query(models.Proof).filter(models.Proof.outcome_id == job_id).all()
        for proof in proofs:
            sub_id = proof.payload_json.get("invite_submission_id") if proof.payload_json else None
            if sub_id:
                sub = db.query(models.InviteSubmission).filter(models.InviteSubmission.id == sub_id).first()
                if sub:
                    sub.status = "submitted" # or "evaluated"
                    db.add(sub)

        db.commit()
        db.refresh(db_eval)
        return db_eval
    return None

def create_feedback(db: Session, feedback: schemas.FeedbackCreate):
    eval_id = None
    if isinstance(feedback.evaluation_id, int):
        eval_id = feedback.evaluation_id
    elif isinstance(feedback.evaluation_id, str) and feedback.evaluation_id.isdigit():
        eval_id = int(feedback.evaluation_id)
    if eval_id is None and feedback.job_id:
        latest_eval = db.query(models.Evaluation).filter(
            models.Evaluation.job_id == feedback.job_id
        ).order_by(desc(models.Evaluation.created_at)).first()
        if latest_eval:
            eval_id = latest_eval.id
    db_feedback = models.Feedback(
        evaluation_id=eval_id,
        job_id=feedback.job_id,
        result=feedback.result,
        metrics_json=feedback.metrics
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

def get_audit_logs(db: Session):
    return db.query(models.AuditLog).order_by(desc(models.AuditLog.created_at)).limit(100).all()

def create_audit_log(db: Session, entity_type: str, entity_id: str, action: str, details: dict = None):
    """Create an audit log entry."""
    db_log = models.AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        details_json=details or {}
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

def get_feedback_list(db: Session):
    """Get all feedback entries for System Learning page."""
    return db.query(models.Feedback).order_by(desc(models.Feedback.created_at)).limit(100).all()
