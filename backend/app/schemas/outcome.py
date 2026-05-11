from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from .task import TaskResponse, TaskCreate

class OutcomeCreate(BaseModel):
    job_id: Optional[str] = None  # Optional for backward compatibility
    title: str
    description: str
    company: str = "SignalStack"
    location: Optional[str] = "Remote"
    category: Optional[str] = "Software Engineering"
    subcategory: Optional[str] = None
    job_type: str = "Full-time"
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = "USD"
    proof_type: str = "github"
    
    # Template fields
    is_template: int = 0
    save_as_template: bool = False  # New flag: If true, creates a Master Template alongside the instance
    source_template_id: Optional[str] = None
    tasks: List[TaskCreate] = []

class OutcomeResponse(OutcomeCreate):
    id: str
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
    is_template: int = 0
    source_template_id: Optional[str] = None
    created_at: datetime
    tasks: List[TaskResponse] = []
    
    class Config:
        from_attributes = True

