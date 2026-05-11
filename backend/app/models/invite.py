from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.config.database import Base
import datetime
import uuid


class Invite(Base):
    """
    A unique invite link for a candidate to apply to a specific job.
    Token-based, no auth needed. Expires after 7 days.
    Status flow: pending → submitted → evaluated
    """
    __tablename__ = "invites"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    token = Column(String, unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Candidate info — filled on submission
    candidate_name = Column(String, nullable=True)
    candidate_email = Column(String, nullable=True)
    github_username = Column(String, nullable=True)
    repo_url = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    resume_url = Column(String, nullable=True)
    leetcode_username = Column(String, nullable=True)
    context = Column(Text, nullable=True)

    # Status
    status = Column(String, default="pending", nullable=False)  # pending | submitted | evaluated

    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    submitted_at = Column(DateTime, nullable=True)

    # Relationships
    job = relationship("Job", backref="invites")
