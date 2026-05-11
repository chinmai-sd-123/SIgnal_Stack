from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from app.config.database import Base
from app.utils.time_utils import utc_now

class Proof(Base):
    __tablename__ = "proofs"

    id = Column(Integer, primary_key=True, index=True)
    outcome_id = Column(String, ForeignKey("outcomes.id"))
    candidate_id = Column(String)
    type = Column(String)  # e.g., "github"
    payload_json = Column(JSON)  # e.g., {"repo_url": "..."}
    snapshot_url = Column(String, nullable=True)
    snapshot_id = Column(String, ForeignKey("snapshots.snapshot_id"), nullable=True)  # Link to immutable snapshot
    preprocessing_checksum = Column(String, nullable=True)  # SHA256 of preprocessed input
    created_at = Column(DateTime, default=utc_now)
