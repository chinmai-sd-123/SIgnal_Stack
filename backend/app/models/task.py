from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.utils.time_utils import utc_now

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)

    outcome_id = Column(
        String,
        ForeignKey("outcomes.id", ondelete="CASCADE"),
        index=True,
        nullable=False
    )
    
    outcome = relationship("Outcome", back_populates="tasks")

    name = Column(String, nullable=False)

    priority = Column(String, nullable=False)   # High | Medium | Low
    weight = Column(Float, nullable=False)      # derived deterministically

    version = Column(Integer, nullable=False)   # snapshot version
    created_at = Column(DateTime, default=utc_now)


class TaskWeightHistory(Base):
    """
    Audit trail for task weight changes.
    Tracks how a task's weight evolves based on feedback.
    """
    __tablename__ = "task_weight_history"

    id = Column(Integer, primary_key=True, index=True)
    
    # Link to the Task (Master Template Task)
    task_id = Column(String, index=True) 
    outcome_id = Column(String, index=True) # Redundant but helpful for queries
    
    old_weight = Column(Float)
    new_weight = Column(Float)
    
    reason = Column(String) # e.g. "Feedback from Job <UUID>"
    feedback_source_job_id = Column(String, nullable=True) # The job instance that triggered this
    
    created_at = Column(DateTime, default=utc_now)
