from sqlalchemy import Column, String, JSON, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.utils.time_utils import utc_now


class Outcome(Base):
    """
    An Outcome is a deliverable goal within a Job.
    Example: For a Backend Engineer job, outcomes might be:
      - Build and maintain core APIs
      - Ensure system reliability and scalability
    Hiring decisions are made at the Outcome level, not the Task level.
    """
    __tablename__ = "outcomes"

    id = Column(String, primary_key=True, index=True)
    
    # Foreign Key to Job
    job_id = Column(
        String,
        ForeignKey("jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=True  # Nullable for migration compatibility
    )

    title = Column(String, nullable=False)  # e.g., "Build and maintain core APIs"
    description = Column(String, nullable=False)
    version = Column(Integer, default=1)
    status = Column(String, default="active")  # active | inprogress | completed

    created_at = Column(DateTime, default=utc_now)
    
    # Template System Fields
    is_template = Column(Integer, default=0)  # 1 = Template, 0 = Instance (Using Integer for SQLite bool compatibility)
    source_template_id = Column(String, nullable=True)  # ID of the template this was cloned from
    # Legacy SEO fields (kept for backward compatibility, prefer Job-level fields)
    slug = Column(String, unique=True, index=True)
    company = Column(String, default="SignalStack")
    location = Column(String)
    category = Column(String)
    subcategory = Column(String)
    category_slug = Column(String, index=True)
    subcategory_slug = Column(String, index=True)
    company_slug = Column(String, index=True)
    location_slug = Column(String, index=True)
    city = Column(String)
    state = Column(String)
    public_url = Column(String)
    last_refreshed_at = Column(DateTime, default=utc_now)
    job_type = Column(String, default="Full-time")
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    currency = Column(String, default="USD")
    
    # Configuration
    proof_type = Column(String, default="github")  # github | artifact | mixed

    # Relationships
    job = relationship("Job", back_populates="outcomes")
    tasks = relationship("Task", back_populates="outcome", cascade="all, delete-orphan")
