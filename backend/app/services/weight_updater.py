"""
Weight Updater Service.

Implements bounded weight updates based on user feedback:
- Clamp weight changes: new_weight = clamp(old + sign * learning_rate, 0, 1)
- Small learning rate and max_delta for stability
- Weight change history for audit trail
- Audit log entries for all changes
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.feedback import SignalWeight, Feedback
from app.models.audit import AuditLog
from app.models.snapshot import SignalWeightHistory


# Learning parameters
DEFAULT_LEARNING_RATE = 0.02  # Small incremental changes
MAX_DELTA = 0.1  # Maximum change per feedback event
MIN_WEIGHT = 0.0
MAX_WEIGHT = 1.0


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max."""
    return max(min_val, min(max_val, value))


def get_current_weight(db: Session, signal_name: str, task_id: str = None) -> float:
    """
    Get current weight for a signal.
    
    Returns default weight (0.5) if not found.
    """
    query = db.query(SignalWeight).filter(SignalWeight.signal_name == signal_name)
    if task_id:
        query = query.filter(SignalWeight.task_id == task_id)
    
    weight_record = query.first()
    if weight_record:
        return weight_record.weight
    
    # Default weights
    defaults = {
        "authorship_fraction": 0.25,
        "tests_present": 0.15,
        "ci_present": 0.10,
        "dockerfile_present": 0.10,
        "schema_present": 0.10,
        "rate_limiting_present": 0.05,
        "readme_quality_score": 0.10,
    }
    return defaults.get(signal_name, 0.1)


def update_weight(
    db: Session,
    signal_name: str,
    feedback_score: float,
    feedback_id: int = None,
    task_id: str = None,
    learning_rate: float = DEFAULT_LEARNING_RATE
) -> Dict[str, Any]:
    """
    Update signal weight based on feedback.
    
    Args:
        db: Database session
        signal_name: Name of the signal to update
        feedback_score: Feedback value (-1 to +1, where positive means increase weight)
        feedback_id: ID of the feedback record (for audit)
        task_id: Optional task context
        learning_rate: Learning rate for update
    
    Returns:
        Dictionary with old_weight, new_weight, and change details
    """
    old_weight = get_current_weight(db, signal_name, task_id)
    
    # Calculate delta with bounds
    raw_delta = feedback_score * learning_rate
    bounded_delta = clamp(raw_delta, -MAX_DELTA, MAX_DELTA)
    
    # Calculate new weight with clamp
    new_weight = clamp(old_weight + bounded_delta, MIN_WEIGHT, MAX_WEIGHT)
    
    # Update or create weight record
    query = db.query(SignalWeight).filter(SignalWeight.signal_name == signal_name)
    if task_id:
        query = query.filter(SignalWeight.task_id == task_id)
    
    weight_record = query.first()
    if weight_record:
        weight_record.weight = new_weight
        weight_record.updated_at = datetime.utcnow()
    else:
        weight_record = SignalWeight(
            signal_name=signal_name,
            task_id=task_id,
            weight=new_weight
        )
        db.add(weight_record)
    
    # Create history record
    history = SignalWeightHistory(
        signal_name=signal_name,
        old_weight=str(old_weight),
        new_weight=str(new_weight),
        change_reason="feedback_update",
        feedback_id=feedback_id
    )
    db.add(history)
    
    # Create audit log entry
    audit_log = AuditLog(
        entity_type="signal_weight",
        entity_id=signal_name,
        action="weight_update",
        details_json={
            "old_weight": old_weight,
            "new_weight": new_weight,
            "delta": new_weight - old_weight,
            "feedback_score": feedback_score,
            "feedback_id": feedback_id,
            "task_id": task_id
        }
    )
    db.add(audit_log)
    
    db.commit()
    
    return {
        "signal_name": signal_name,
        "old_weight": old_weight,
        "new_weight": new_weight,
        "delta": new_weight - old_weight,
        "bounded": abs(raw_delta) > MAX_DELTA
    }


def process_feedback_updates(
    db: Session,
    evaluation_id: int,
    result: str,
    metrics: Dict[str, Any] = None,
    feedback_id: int = None
) -> List[Dict[str, Any]]:
    """
    Process feedback and update relevant weights.
    
    Args:
        db: Database session
        evaluation_id: ID of the evaluation being reviewed
        result: 'success' or 'failure'
        metrics: Optional specific signal feedback {signal_name: score}
        feedback_id: ID of feedback record
    
    Returns:
        List of weight update results
    """
    changes = []
    
    # Base score: +1 for success, -1 for failure
    base_score = 1.0 if result == "success" else -1.0
    
    if metrics:
        # Specific signal feedback
        for signal_name, score in metrics.items():
            if isinstance(score, (int, float)):
                result = update_weight(
                    db=db,
                    signal_name=signal_name,
                    feedback_score=score * base_score,
                    feedback_id=feedback_id
                )
                changes.append(result)
    else:
        # General feedback - apply smaller updates to all signals
        default_signals = [
            "authorship_fraction",
            "tests_present", 
            "ci_present",
            "dockerfile_present",
            "schema_present",
            "readme_quality_score"
        ]
        
        for signal_name in default_signals:
            result = update_weight(
                db=db,
                signal_name=signal_name,
                feedback_score=base_score * 0.5,  # Smaller impact for general feedback
                feedback_id=feedback_id,
                learning_rate=DEFAULT_LEARNING_RATE * 0.5
            )
            changes.append(result)
    
    return changes


def get_weight_history(db: Session, signal_name: str = None, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get weight change history for audit.
    """
    query = db.query(SignalWeightHistory)
    if signal_name:
        query = query.filter(SignalWeightHistory.signal_name == signal_name)
    
    history = query.order_by(SignalWeightHistory.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": h.id,
            "signal_name": h.signal_name,
            "old_weight": h.old_weight,
            "new_weight": h.new_weight,
            "change_reason": h.change_reason,
            "feedback_id": h.feedback_id,
            "created_at": h.created_at.isoformat() if h.created_at else None
        }
        for h in history
    ]


def admin_override_weight(
    db: Session,
    signal_name: str,
    new_weight: float,
    reason: str = "admin_override",
    task_id: str = None
) -> Dict[str, Any]:
    """
    Allow admin to directly set a weight value.
    
    This bypasses the bounded learning and allows direct control.
    """
    old_weight = get_current_weight(db, signal_name, task_id)
    new_weight = clamp(new_weight, MIN_WEIGHT, MAX_WEIGHT)
    
    # Update weight
    query = db.query(SignalWeight).filter(SignalWeight.signal_name == signal_name)
    if task_id:
        query = query.filter(SignalWeight.task_id == task_id)
    
    weight_record = query.first()
    if weight_record:
        weight_record.weight = new_weight
        weight_record.updated_at = datetime.utcnow()
    else:
        weight_record = SignalWeight(
            signal_name=signal_name,
            task_id=task_id,
            weight=new_weight
        )
        db.add(weight_record)
    
    # Create history record
    history = SignalWeightHistory(
        signal_name=signal_name,
        old_weight=str(old_weight),
        new_weight=str(new_weight),
        change_reason=reason,
        feedback_id=None
    )
    db.add(history)
    
    # Create audit log
    audit_log = AuditLog(
        entity_type="signal_weight",
        entity_id=signal_name,
        action="admin_override",
        details_json={
            "old_weight": old_weight,
            "new_weight": new_weight,
            "reason": reason
        }
    )
    db.add(audit_log)
    
    db.commit()
    
    return {
        "signal_name": signal_name,
        "old_weight": old_weight,
        "new_weight": new_weight,
        "reason": reason
    }
