from pydantic import BaseModel, EmailStr
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
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True
