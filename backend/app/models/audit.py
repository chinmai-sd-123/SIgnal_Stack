from sqlalchemy import Column, Integer, String, JSON, DateTime
from app.config.database import Base
from app.utils.time_utils import utc_now

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String)
    entity_id = Column(String)
    action = Column(String)
    details_json = Column(JSON)
    created_at = Column(DateTime, default=utc_now)
