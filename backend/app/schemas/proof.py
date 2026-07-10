from pydantic import BaseModel
from typing import Any, Dict, Optional

class ProofCreate(BaseModel):
    job_id: Optional[str] = None # Optional in schema, but required for submission logic
    candidate_id: str
    type: str
    payload: Dict[str, Any]

class Evidence(BaseModel):
    type: str
    ref: str
    snippet: str
    source_url: Optional[str] = None
