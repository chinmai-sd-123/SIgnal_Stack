from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Integer, JSON
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.utils.time_utils import utc_now
import uuid


class Invite(Base):
    """
    A reusable invite link for a job. Multiple candidates can submit through
    the same link. Expires after 7 days. Recruiter can revoke at any time.
    """
    __tablename__ = "invites"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    token = Column(String, unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Status: active (accepting submissions) | revoked (manually disabled)
    status = Column(String, default="active", nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=utc_now)
    expires_at = Column(DateTime, nullable=False)

    # Relationships
    job = relationship("Job", backref="invites")
    submissions = relationship("InviteSubmission", back_populates="invite", cascade="all, delete-orphan")


class InviteSubmission(Base):
    """
    A single candidate's submission through an invite link.
    Each submission captures all candidate-provided info.
    """
    __tablename__ = "invite_submissions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    invite_id = Column(String, ForeignKey("invites.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)

    # Candidate info
    candidate_name = Column(String, nullable=False)
    candidate_email = Column(String, nullable=False)
    github_username = Column(String, nullable=True)
    repo_url = Column(String, nullable=True)
    # Up to 3 repositories relevant to the JD. repo_url stays as the primary
    # (first) repo for backward compatibility with older submissions.
    repo_urls = Column(JSON, nullable=True)
    linkedin_url = Column(String, nullable=True)
    resume_url = Column(String, nullable=True)
    leetcode_username = Column(String, nullable=True)
    context = Column(Text, nullable=True)

    # Status: submitted | evaluated
    status = Column(String, default="submitted", nullable=False)

    # Timestamps
    submitted_at = Column(DateTime, default=utc_now)

    # Relationships
    invite = relationship("Invite", back_populates="submissions")
