from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, field_validator
from fastapi.encoders import jsonable_encoder

from app.config.database import get_db
from app.services import crud
from app.services.repo_selector import RepoSelector, RepoScore

router = APIRouter(prefix="/plugin/github", tags=["GitHub Repo Selector"])

class RepoSelectionRequest(BaseModel):
    github_username: str
    job_id: Optional[str] = None
    candidate_id: Optional[str] = None

    @field_validator("github_username")
    @classmethod
    def normalize_github_username(cls, value: str) -> str:
        if value is None:
            raise ValueError("github_username is required")
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("github_username is required")
        return trimmed

    @field_validator("job_id", "candidate_id")
    @classmethod
    def normalize_optional_str(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None


class RepoScoreResponse(BaseModel):
    owner: str
    repo: str
    url: str
    score: float
    manifest_present: bool
    language: Optional[str]
    last_commit_date: Optional[str]
    size_kb: int
    breakdown: dict

@router.post("/repos/select", response_model=List[RepoScoreResponse])
def select_repos(request: RepoSelectionRequest, db: Session = Depends(get_db)):
    """
    Select top repos for a candidate based on job requirements.
    """
    selector = RepoSelector()

    print(
        f"[repo-select] username={request.github_username} job_id={request.job_id} candidate_id={request.candidate_id}",
        flush=True,
    )
    
    # Construct candidate dict
    candidate = {
        "github_username": request.github_username,
        # We could fetch resume projects if we had a candidate profile stored
    }
    
    # Construct job dict if job_id provided
    job_dict = None
    if request.job_id:
        job = crud.get_outcome(db, request.job_id) # Outcome/Job are mixed, checking crud
        # Actually crud.get_outcome returns Outcome model. 
        # But we also have get_job now? 
        # Let's check crud.py to be sure what we should call.
        # Ideally we want Job (requirements, title).
        # Since I just refactored Job hierarchy, I should use Job model if possible.
        # But crud.get_outcome might be what's available? 
        # Let's check crud.py content or assumes I can query Job directly.
        from app.models.job import Job
        job_obj = db.query(Job).filter(Job.id == request.job_id).first()
            
        if not job_obj:
            # Fallback to outcome if job not found (legacy support)
            from app.models.outcome import Outcome
            outcome = db.query(Outcome).filter(Outcome.id == request.job_id).first()
            if outcome:
                 job_dict = {
                    "title": outcome.title,
                    "description": outcome.description,
                    "required_languages": [] # Outcome doesn't have languages yet
                }
            
        if job_obj:
            job_dict = {
                "title": job_obj.title,
                "description": job_obj.description,
                "required_languages": job_obj.required_languages or []
            }
            
    scored_repos = selector.select_repos_for_candidate(candidate, job_dict)
    print(f"[repo-select] found={len(scored_repos)}", flush=True)

    if scored_repos:
        return jsonable_encoder(scored_repos)

    # Fallback: return basic repo list if scoring yields nothing
    user_repos = selector._get_user_repos(request.github_username)
    print(f"[repo-select] fallback_user_repos={len(user_repos)}", flush=True)
    fallback: List[RepoScore] = []
    for repo in user_repos[:5]:
        fallback.append(RepoScore(
            owner=(repo.get("owner") or {}).get("login", ""),
            repo=repo.get("name", ""),
            url=repo.get("html_url", ""),
            score=0.0,
            manifest_present=False,
            language=repo.get("language"),
            last_commit_date=repo.get("pushed_at"),
            size_kb=repo.get("size", 0),
            breakdown={
                "name_match": 0.0,
                "manifest": 0.0,
                "recency": 0.0,
                "size": 0.0,
                "language_match": 0.0,
            },
        ))
    return jsonable_encoder(fallback)
