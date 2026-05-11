from pydantic import BaseModel
from typing import List

# What user sends when creating/editing a task
class TaskCreate(BaseModel):
    name: str           # task title (matches DB column name)
    priority: str       # High | Medium | Low
    weight: float = 0.0 # Optional initial weight

# What LLM returns (suggested tasks before user accepts)
class TaskSuggestion(BaseModel):
    name: str           # suggested task title
    priority: str       # suggested priority (High/Medium/Low)

# When user submits all accepted/edited tasks
class TaskBatchCreate(BaseModel):
    outcome_id: str
    tasks: List[TaskCreate]

class TaskResponse(BaseModel):
    id: str
    outcome_id: str
    name: str
    priority: str
    weight: float
    version: int

    class Config:
        from_attributes = True

class TaskSuggestionRequest(BaseModel):
    description: str