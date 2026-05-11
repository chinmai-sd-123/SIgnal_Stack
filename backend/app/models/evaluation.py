from sqlalchemy import Column, Integer, String, JSON, Float, DateTime, ForeignKey
from app.config.database import Base
from app.utils.time_utils import utc_now

class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, ForeignKey("outcomes.id")) # Using outcome_id as job_id for simplicity in MVP
    outcome_id = Column(String, ForeignKey("outcomes.id"))
    snapshot_id = Column(String, ForeignKey("snapshots.snapshot_id"), nullable=True)  # Link to snapshot
    status = Column(String, default="pending")  # pending, processing, completed, failed
    evaluation_json = Column(JSON)  # Full evaluation trace
    fit_score = Column(Float)
    work_allocation = Column(JSON, nullable=True)  # Allocation result
    confidence = Column(Float, nullable=True)  # Confidence score
    risk_flags = Column(JSON, nullable=True)  # e.g., ["low_authorship", "partial_coverage"]
    created_at = Column(DateTime, default=utc_now)
