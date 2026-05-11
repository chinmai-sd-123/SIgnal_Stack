from sqlalchemy import Column, String, ForeignKey, Float, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from app.config.database import Base
import datetime


class JobCandidate(Base):
    """
    Tracks individual candidates applying for a job.
    Status flow: applied → evaluated → shortlisted/rejected
    """
    __tablename__ = "job_candidates"
    
    id = Column(String, primary_key=True, index=True)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(String, nullable=False)  # GitHub username or identifier
    
    # Evaluation Results
    status = Column(String, default="applied", nullable=False)  # applied | evaluated | shortlisted | rejected
    evaluation_score = Column(Float, nullable=True)  # Overall score (0-100)
    outcome_coverage = Column(Float, nullable=True)  # Percentage of outcomes covered
    
    # Metadata
    applied_at = Column(DateTime, default=datetime.datetime.utcnow)
    evaluated_at = Column(DateTime, nullable=True)
    shortlisted_at = Column(DateTime, nullable=True)
    
    # Raw evaluation data
    evaluation_data = Column(JSON, nullable=True)  # Task scores, outcome breakdown, etc.
    
    # Relationships
    job = relationship("Job", backref="candidates")
    
    __table_args__ = (
        # Each candidate can only apply once per job
        UniqueConstraint('job_id', 'candidate_id', name='unique_candidate_per_job'),
    )
