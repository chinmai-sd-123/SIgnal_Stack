from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime


class JobBase(BaseModel):
    title: str
    description: Optional[str] = None
    company: str = "SignalStack"
    location: Optional[str] = "Remote"
    category: Optional[str] = "Software Engineering"
    subcategory: Optional[str] = None
    job_type: str = "Full-time"
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = "USD"
    required_languages: List[str] = []


class JobCreate(JobBase):
    pass


class OutcomeMinimal(BaseModel):
    """Minimal outcome info for job listings."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    status: str = "active"


class JobResponse(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    recruiter_id: Optional[str] = None
    slug: Optional[str] = None
    category_slug: Optional[str] = None
    subcategory_slug: Optional[str] = None
    company_slug: Optional[str] = None
    location_slug: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    public_url: Optional[str] = None
    last_refreshed_at: Optional[datetime] = None
    status: str
    version: int
    created_at: datetime
    # Include outcomes for job dashboard
    outcomes: List[OutcomeMinimal] = []
