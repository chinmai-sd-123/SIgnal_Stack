from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import app.schemas as schemas
from app.config.database import get_db
from app.services import crud
from app.pipeline.signal_extractor import SignalExtractor
from app.services.leetcode import LeetCodeService

router = APIRouter(tags=["Signal Extractor"])

@router.post("/proofs", response_model=schemas.ProofCreate)
def submit_proof(proof: schemas.ProofCreate, db: Session = Depends(get_db)):
    # Verify outcome exists
    if proof.job_id:
        outcome = crud.get_outcome(db, proof.job_id)
        if not outcome:
            raise HTTPException(status_code=404, detail="Outcome not found")
    result = crud.create_proof(db, proof)
    # Audit Log
    crud.create_audit_log(db, "proof", proof.job_id, "submitted", {"candidate": proof.candidate_id, "type": proof.type})
    return result

@router.get("/proofs/{job_id}", response_model=List[schemas.ProofCreate])
def get_proofs(job_id: str, db: Session = Depends(get_db)):
    proofs = crud.get_proofs(db, job_id)
    return [schemas.ProofCreate(
        job_id=p.outcome_id,
        candidate_id=p.candidate_id,
        type=p.type,
        payload=p.payload_json
    ) for p in proofs]

@router.get("/plugin/repo-preview")
def get_repo_preview(repo_url: str):
    if not repo_url or "github.com" not in repo_url:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")
    
    extractor = SignalExtractor()
    files, default_branch = extractor.github.get_recursive_tree(repo_url)
    if not files:
        return {"name": "Repository Not Found", "files": [], "readme": ""}
        
    # Fetch README
    readme_content = ""
    readme_file = next((f for f in files if f.lower().startswith('readme')), None)
    if readme_file:
        readme_content = extractor.github.get_file_content(repo_url, readme_file)
        
    return {
        "name": repo_url.rstrip('/').split('/')[-1],
        "files": files[:10], # Limit to top 10 for preview
        "readme": readme_content[:500] + "..." if len(readme_content) > 500 else readme_content
    }

@router.get("/plugin/leetcode/{username}")
def get_leetcode_stats(username: str):
    service = LeetCodeService()
    return service.fetch_stats(username)
