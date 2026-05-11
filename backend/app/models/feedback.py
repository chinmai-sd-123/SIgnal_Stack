from sqlalchemy import Column, Integer, String, JSON, Float, DateTime, ForeignKey
from app.config.database import Base
import datetime

class SignalWeight(Base):
    __tablename__ = "signal_weights"

    id = Column(Integer, primary_key=True, index=True)
    signal_name = Column(String, index=True)
    task_id = Column(String, nullable=True) # Context specific
    weight = Column(Float)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"))
    job_id = Column(String)
    result = Column(String) # success | failure
    metrics_json = Column(JSON)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
