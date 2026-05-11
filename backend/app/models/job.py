from sqlalchemy import Column, String, JSON, DateTime, Integer, Boolean, Float
from sqlalchemy.orm import relationship
from app.config.database import Base
from app.utils.time_utils import utc_now


class Job(Base):
    """
    A Job represents a position to be filled (e.g., Backend Engineer).
    A Job has multiple Outcomes, each representing a deliverable goal.
    Hiring decisions are made at the Outcome level.
    """
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)  # e.g., "Backend Engineer"
    description = Column(String, nullable=True)
    version = Column(Integer, default=1)
    status = Column(String, default="active")  # active | closed | archived
    
    # Shortlist Management
    applications_open = Column(Boolean, default=True, nullable=False)
    total_positions = Column(Integer, default=1, nullable=False)  # Used for shortlist sizing
    shortlist_multiplier = Column(Float, default=3.0, nullable=False)  # Shortlist = positions × multiplier

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # SEO & Job Board Fields (moved from Outcome)
    slug = Column(String, unique=True, index=True)
    company = Column(String, default="SignalStack")
    location = Column(String)
    category = Column(String)
    subcategory = Column(String)
    
    # Advanced SEO Fields
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

    # Language/Tech requirements for repo matching
    required_languages = Column(JSON, default=list)  # e.g., ["python", "javascript"]

    # Relationships
    outcomes = relationship("Outcome", back_populates="job", cascade="all, delete-orphan")
    
    @property
    def shortlist_size(self):
        """Calculate recommended shortlist size"""
        return int(self.total_positions * self.shortlist_multiplier)
    
    @property
    def is_accepting_applications(self):
        """Check if job accepts new applications"""
        return self.status == "active" and self.applications_open
