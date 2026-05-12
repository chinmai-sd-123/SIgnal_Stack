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


class RecruiterSignup(RecruiterBase):
    password: str
    invite_token: str


class RecruiterResponse(RecruiterBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str = "recruiter"
    created_at: datetime


class RecruiterAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    recruiter: RecruiterResponse


class RecruiterInviteCreate(BaseModel):
    email: EmailStr
    name: Optional[str] = None


class RecruiterInviteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    name: Optional[str] = None
    token: str
    status: str
    invited_by: Optional[str] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    used_at: Optional[datetime] = None
