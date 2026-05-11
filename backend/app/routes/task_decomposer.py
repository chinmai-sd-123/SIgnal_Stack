from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
import app.schemas as schemas
from app.config.database import get_db
from app.services import crud
from app.pipeline.task_decomposer import TaskDecomposer

router = APIRouter(tags=["Task Decomposer"])

@router.post("/plugin/suggest-tasks", response_model=List[schemas.TaskSuggestion])
def suggest_tasks(request: schemas.TaskSuggestionRequest):
    decomposer = TaskDecomposer()
    return decomposer.split(request.description)

@router.post("/tasks/batch", response_model=List[schemas.TaskResponse]) 
def create_tasks_batch(batch: schemas.TaskBatchCreate, db: Session = Depends(get_db)):
    # Verify outcome exists
    outcome = crud.get_outcome(db, batch.outcome_id)
    if not outcome:
        raise HTTPException(status_code=404, detail="Outcome not found")
        
    tasks = crud.create_tasks_batch(db, batch)
    return tasks
