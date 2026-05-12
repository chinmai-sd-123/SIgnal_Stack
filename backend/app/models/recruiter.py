import uuid
from sqlalchemy import Column, String, DateTime, func
from app.config.database import Base

class Recruiter(Base):
    __tablename__ = "recruiters"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=True) # Optional now as per flow
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="recruiter", nullable=False)
    created_at = Column(DateTime, default=func.now())
