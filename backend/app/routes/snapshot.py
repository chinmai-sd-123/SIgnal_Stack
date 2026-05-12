"""
Snapshot API Routes.

Provides endpoints for:
- GET /snapshots/{snapshot_id}/signals - Get signals from a snapshot
- GET /snapshots/{snapshot_id}/metadata - Get snapshot metadata
- POST /snapshots - Create a new snapshot (internal)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.config.database import get_db
from app.models.job import Job
from app.models.outcome import Outcome
from app.models.recruiter import Recruiter
from app.services.auth import ensure_job_access, get_current_recruiter
from app.pipeline.snapshotter import (
    get_snapshot,
    get_snapshot_files,
    get_snapshot_metadata,
    verify_snapshot_integrity
)

router = APIRouter(prefix="/snapshots", tags=["Snapshots"])


def _ensure_snapshot_access(db: Session, snapshot_id: str, current: Recruiter):
    if current.role == "admin":
        return

    from app.models.evaluation import Evaluation

    evaluation = db.query(Evaluation).filter(Evaluation.snapshot_id == snapshot_id).first()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    outcome_id = evaluation.outcome_id or evaluation.job_id
    outcome = db.query(Outcome).filter(Outcome.id == outcome_id).first()
    if not outcome or not outcome.job_id:
        raise HTTPException(status_code=404, detail="Snapshot not found")

    job = db.query(Job).filter(Job.id == outcome.job_id).first()
    ensure_job_access(job, current)


@router.get("/{snapshot_id}")
def get_snapshot_info(
    snapshot_id: str,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """Get snapshot information."""
    snapshot = get_snapshot(db, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    _ensure_snapshot_access(db, snapshot_id, current)
    
    return {
        "snapshot_id": snapshot.snapshot_id,
        "repo_url": snapshot.repo_url,
        "commit_hash": snapshot.commit_hash,
        "file_count": snapshot.file_count,
        "checksum": snapshot.checksum,
        "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
        "integrity_verified": verify_snapshot_integrity(snapshot_id, db)
    }


@router.get("/{snapshot_id}/signals")
def get_snapshot_signals(
    snapshot_id: str,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """
    Get extracted signals from a snapshot.
    
    Returns the signals that were extracted during evaluation.
    """
    snapshot = get_snapshot(db, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    _ensure_snapshot_access(db, snapshot_id, current)
    
    # Signals are stored in the evaluation, linked via snapshot_id
    from app.models.evaluation import Evaluation
    evaluation = db.query(Evaluation).filter(
        Evaluation.snapshot_id == snapshot_id
    ).first()
    
    if evaluation and evaluation.evaluation_json:
        return {
            "snapshot_id": snapshot_id,
            "signals": evaluation.evaluation_json.get("signals", {}),
            "scoring": evaluation.evaluation_json.get("scoring", {}),
        }
    
    # Return metadata if no evaluation found
    metadata = get_snapshot_metadata(snapshot_id)
    return {
        "snapshot_id": snapshot_id,
        "signals": {},
        "metadata": metadata,
        "message": "No evaluation associated with this snapshot"
    }


@router.get("/{snapshot_id}/files")
def get_snapshot_file_list(
    snapshot_id: str,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """Get list of files stored in a snapshot."""
    snapshot = get_snapshot(db, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    _ensure_snapshot_access(db, snapshot_id, current)
    
    files = get_snapshot_files(snapshot_id)
    return {
        "snapshot_id": snapshot_id,
        "file_count": len(files),
        "files": list(files.keys())
    }


@router.get("/{snapshot_id}/files/{filename}")
def get_snapshot_file_content(
    snapshot_id: str,
    filename: str,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """Get content of a specific file from a snapshot."""
    snapshot = get_snapshot(db, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    _ensure_snapshot_access(db, snapshot_id, current)
    
    files = get_snapshot_files(snapshot_id)
    if filename not in files:
        raise HTTPException(status_code=404, detail="File not found in snapshot")
    
    return {
        "snapshot_id": snapshot_id,
        "filename": filename,
        "content": files[filename]
    }


@router.get("/{snapshot_id}/verify")
def verify_snapshot(
    snapshot_id: str,
    db: Session = Depends(get_db),
    current: Recruiter = Depends(get_current_recruiter),
):
    """Verify snapshot integrity."""
    snapshot = get_snapshot(db, snapshot_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    _ensure_snapshot_access(db, snapshot_id, current)
    
    is_valid = verify_snapshot_integrity(snapshot_id, db)
    
    return {
        "snapshot_id": snapshot_id,
        "integrity_valid": is_valid,
        "stored_checksum": snapshot.checksum,
        "message": "Snapshot integrity verified" if is_valid else "INTEGRITY CHECK FAILED - snapshot may have been modified"
    }
