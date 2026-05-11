from sqlalchemy import Column, Integer, String, JSON, DateTime, Text
from app.config.database import Base
import datetime

class Snapshot(Base):
    """Immutable snapshot of a repository state for reproducible evaluations."""
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_id = Column(String, unique=True, index=True)  # UUID for external reference
    repo_url = Column(String, nullable=False)
    commit_hash = Column(String, nullable=False)
    author_map = Column(JSON)  # {author_email: {commits: N, lines: M}}
    file_count = Column(Integer)
    metadata_json = Column(JSON)  # Additional metadata (branch, tags, etc.)
    files_path = Column(String)  # Path to stored files on disk
    checksum = Column(String)  # SHA256 of the snapshot content
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class LLMLog(Base):
    """Audit log for all LLM (OpenAI) interactions."""
    __tablename__ = "llm_logs"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(Integer, nullable=True)  # Link to evaluation if applicable
    prompt = Column(Text)
    raw_response = Column(Text)
    validated_json = Column(JSON, nullable=True)  # Parsed and validated response
    is_valid = Column(Integer, default=1)  # 1 = valid, 0 = fallback used
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class SignalWeightHistory(Base):
    """History of signal weight changes for audit trail."""
    __tablename__ = "signal_weight_history"

    id = Column(Integer, primary_key=True, index=True)
    signal_name = Column(String, nullable=False)
    old_weight = Column(String)  # Stored as string to preserve precision
    new_weight = Column(String)
    change_reason = Column(String)  # e.g., "feedback_update", "admin_override"
    feedback_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
