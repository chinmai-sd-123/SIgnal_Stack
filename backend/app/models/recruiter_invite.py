import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from app.config.database import Base
from app.utils.time_utils import utc_now


class RecruiterInvite(Base):
    __tablename__ = "recruiter_invites"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, index=True, nullable=False)
    name = Column(String, nullable=True)
    token = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="active", nullable=False)
    invited_by = Column(String, ForeignKey("recruiters.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now)
    expires_at = Column(DateTime, nullable=True)
    used_at = Column(DateTime, nullable=True)
