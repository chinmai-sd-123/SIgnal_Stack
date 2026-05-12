from pydantic import BaseModel, ConfigDict, EmailStr
from datetime import datetime
from typing import Optional

class RecruiterBase(BaseModel):
    name: Optional[str] = None
    email: EmailStr

class RecruiterCreate(RecruiterBase):
    password: str

class RecruiterLogin(BaseModel):
    email: EmailStr
    password: str

class RecruiterResponse(RecruiterBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str = "recruiter"
    created_at: datetime


class RecruiterAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    recruiter: RecruiterResponse
