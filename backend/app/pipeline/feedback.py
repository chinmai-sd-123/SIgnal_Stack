import logging
from typing import List, Dict, Any

from sqlalchemy.orm import Session
import app.models as models
import app.schemas as schemas
from app.services.weight_updater import update_weight


logger = logging.getLogger(__name__)

class FeedbackLoop:
    def __init__(self, db: Session):
        self.db = db

    def process_feedback(self, feedback: models.Feedback) -> List[str]:
        changes = []
        if feedback.evaluation_id:
            eval_id = None
            if isinstance(feedback.evaluation_id, int):
                eval_id = feedback.evaluation_id
            elif isinstance(feedback.evaluation_id, str) and feedback.evaluation_id.isdigit():
                eval_id = int(feedback.evaluation_id)
            
            eval_db = None
            if eval_id:
                eval_db = self.db.query(models.Evaluation).filter(models.Evaluation.id == eval_id).first()
            
            if not eval_db and feedback.job_id:
                 eval_db = self.db.query(models.Evaluation).filter(models.Evaluation.job_id == feedback.job_id).first()
                 
            if eval_db:
                eval_data = eval_db.evaluation_json
                signals_used = eval_data.get("global_signals_used", [])
                
                # Adjust weights based on result
                feedback_score = 1.0 if feedback.result == "success" else -1.0
                
                for signal in signals_used:
                    result = update_weight(
                        self.db,
                        signal_name=signal,
                        feedback_score=feedback_score,
                        feedback_id=feedback.id,
                    )
                    changes.append(
                        f"Updated {signal}: {result['old_weight']:.2f} -> {result['new_weight']:.2f}"
                    )
        
        if not changes:
            changes.append("No signals found to update")
            
        return changes

    def process_task_feedback(self, request: schemas.TaskWeightFeedbackRequest) -> Dict[str, Any]:
        logger.debug("Processing feedback for Job ID: '%s'", request.job_id)
        
        # 1. Find Job & Outcome Instance
        from sqlalchemy import or_
        outcome_instance = self.db.query(models.Outcome).filter(
            or_(models.Outcome.job_id == request.job_id, models.Outcome.id == request.job_id)
        ).first()
        if not outcome_instance:
             raise ValueError("Job/Outcome not found")

        changes_log = []
        DELTA = 0.15

        # === SCOPE A: Update INSTANCE (Current Job) ===
        instance_task = next((t for t in outcome_instance.tasks if t.name == request.task_name), None)
        if instance_task:
            old_inst_weight = instance_task.weight
            
            # Calc new weight
            if request.direction == "boost":
                new_inst_weight = min(0.9, old_inst_weight + DELTA)
            else:
                new_inst_weight = max(0.1, old_inst_weight - DELTA)
            
            actual_delta_inst = new_inst_weight - old_inst_weight
            
            if actual_delta_inst != 0:
                # Update Target
                instance_task.weight = new_inst_weight
                self.db.add(instance_task)
                changes_log.append(f"[Current Job] Updated '{instance_task.name}': {old_inst_weight:.2f} -> {new_inst_weight:.2f}")
                
                # Redistribute in Instance
                other_inst_tasks = [t for t in outcome_instance.tasks if t.id != instance_task.id]
                total_other_inst = sum(t.weight for t in other_inst_tasks)
                
                if other_inst_tasks and total_other_inst > 0:
                    for t in other_inst_tasks:
                        share = t.weight / total_other_inst
                        reduction = actual_delta_inst * share
                        t.weight = max(0.05, t.weight - reduction)
                        self.db.add(t)
        else:
            changes_log.append(f"WARNING: Task '{request.task_name}' not found in current job instance.")

        # === SCOPE B: Update MASTER TEMPLATE (Future Jobs) ===
        master_template_id = outcome_instance.source_template_id
        if master_template_id:
            master_template = self.db.query(models.Outcome).filter(models.Outcome.id == master_template_id).first()
            if master_template:
                # CRITICAL: Refresh to ensure we are editing the latest state
                self.db.refresh(master_template)
                
                master_task = self.db.query(models.Task).filter(
                    models.Task.outcome_id == master_template.id, 
                    models.Task.name == request.task_name
                ).first()

                if master_task:
                    old_master_weight = master_task.weight
                    
                    # Calc new weight (same logic)
                    if request.direction == "boost":
                        new_master_weight = min(0.9, old_master_weight + DELTA)
                    else:
                        new_master_weight = max(0.1, old_master_weight - DELTA)
                        
                    actual_delta_master = new_master_weight - old_master_weight
                    
                    if actual_delta_master != 0:
                        master_task.weight = new_master_weight
                        self.db.add(master_task)
                        changes_log.append(f"[Master Template] Updated '{master_task.name}': {old_master_weight:.2f} -> {new_master_weight:.2f}")
                        
                        # Log History (Only need to log once per logical feedback, linking to Master is good)
                        self._log_history(master_task.id, master_template.id, old_master_weight, new_master_weight, request.reason, request.job_id)

                        # Redistribute in Master
                        # Explicitly Query Others
                        other_master_tasks = self.db.query(models.Task).filter(
                            models.Task.outcome_id == master_template.id,
                            models.Task.id != master_task.id
                        ).all()
                        
                        total_other_master = sum(t.weight for t in other_master_tasks)
                        
                        if other_master_tasks and total_other_master > 0:
                            for t in other_master_tasks:
                                share = t.weight / total_other_master
                                reduction = actual_delta_master * share
                                t.weight = max(0.05, t.weight - reduction)
                                self.db.add(t)
            else:
                changes_log.append("Master template ID found but template missing in DB.")
        else:
            changes_log.append("No Master Template linked. Only updated current job.")
            
        self.db.commit()
        
        return {
            "status": "success", 
            "changes": changes_log,
            # Return new weights from INSTANCE so frontend updates immediately if needed
            "new_weights": {t.name: round(t.weight, 2) for t in outcome_instance.tasks}
        }

    def _log_history(self, task_id, outcome_id, old, new, reason, source_job):
        from app.models.task import TaskWeightHistory
        history = TaskWeightHistory(
            task_id=task_id,
            outcome_id=outcome_id,
            old_weight=old,
            new_weight=new,
            reason=reason,
            feedback_source_job_id=source_job
        )
        self.db.add(history)

    def revert_task_feedback(self, job_id: str) -> List[str]:
        """
        Reverts any task weight adjustments made by a specific job.
        Used when a decision is Reset.
        """
        from app.models.task import TaskWeightHistory, Task
        
        # Find all history entries for this job
        history_entries = self.db.query(TaskWeightHistory).filter(
            TaskWeightHistory.feedback_source_job_id == job_id
        ).all()
        
        changes = []
        
        for entry in history_entries:
            # Revert the MASTER Task
            task = self.db.query(Task).filter(Task.id == entry.task_id).first()
            if task:
                # We revert to old_weight. 
                # Note: If multiple feedbacks happened, this might be tricky, 
                # but assuming one "Submit" per flow or simple rollback, this is safe.
                # Use current weight? No, revert to what it was BEFORE this specific change.
                # But what if another job changed it in between? 
                # Simple approach: Apply the inverse delta.
                delta = entry.new_weight - entry.old_weight
                
                # Apply inverse to CURRENT weight (to respect other intervening updates)
                reverted_weight = task.weight - delta
                task.weight = max(0.05, reverted_weight) # Safety clamp
                
                self.db.add(task)
                changes.append(f"Reverted {task.name}: {task.weight:.2f} (Delta {-delta:.2f})")
            
            # Remove this history entry so we don't revert again
            self.db.delete(entry)
            
        self.db.commit()
        return changes
