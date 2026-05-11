"""
Snapshotter module for creating immutable repository snapshots.

This module provides functionality to:
1. Clone/fetch a repository at a specific commit
2. Extract metadata (author map, file count, etc.)
3. Store selected files for evidence
4. Generate checksums for reproducibility
"""

import os
import json
import hashlib
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.models.snapshot import Snapshot
from app.config.database import get_db


# Base path for storing snapshots
SNAPSHOT_STORAGE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "snapshots"
)


def ensure_storage_dir():
    """Ensure the snapshot storage directory exists."""
    os.makedirs(SNAPSHOT_STORAGE_PATH, exist_ok=True)


def generate_snapshot_id() -> str:
    """Generate a unique snapshot ID."""
    return f"snap_{uuid.uuid4().hex[:16]}"


def calculate_checksum(data: str) -> str:
    """Calculate SHA256 checksum of data."""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()


def create_snapshot(
    db: Session,
    repo_url: str,
    commit_hash: str,
    author_map: Dict[str, Any],
    files_content: Dict[str, str],
    metadata: Optional[Dict[str, Any]] = None,
    file_tree: Optional[List[str]] = None,
    top_committers: Optional[List[str]] = None,
    total_commits: int = 0,
    languages: Optional[List[str]] = None
) -> Snapshot:
    """
    Create an immutable snapshot of repository state.
    
    Args:
        db: Database session
        repo_url: URL of the repository
        commit_hash: Git commit hash
        author_map: Mapping of authors to their contributions
        files_content: Dictionary of file paths to their content (selected files only, max 20)
        metadata: Additional metadata (branch, tags, etc.)
        file_tree: Complete list of file paths in the repo
        top_committers: List of top committer names/emails
        total_commits: Total commit count
        languages: Detected languages in the repo
    
    Returns:
        Created Snapshot object
    """
    ensure_storage_dir()
    
    snapshot_id = generate_snapshot_id()
    snapshot_dir = os.path.join(SNAPSHOT_STORAGE_PATH, snapshot_id)
    os.makedirs(snapshot_dir, exist_ok=True)
    
    # Build enhanced metadata
    metadata_content = {
        "repo_url": repo_url,
        "commit_hash": commit_hash,
        "author_map": author_map,
        "file_count": len(files_content),
        "top_committers": top_committers or [],
        "total_commits": total_commits,
        "languages": languages or [],
        "snapshot_created_at": datetime.utcnow().isoformat(),
        **(metadata or {})
    }
    
    # Save metadata.json
    metadata_path = os.path.join(snapshot_dir, "metadata.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata_content, f, indent=2)
    
    # Save file_tree.json (if provided)
    if file_tree:
        file_tree_path = os.path.join(snapshot_dir, "file_tree.json")
        with open(file_tree_path, 'w', encoding='utf-8') as f:
            json.dump(file_tree, f, indent=2)
    
    # Store selected files and create snippets
    files_dir = os.path.join(snapshot_dir, "files")
    os.makedirs(files_dir, exist_ok=True)
    
    all_content = ""
    for file_path, content in files_content.items():
        # Sanitize file path for storage
        safe_path = file_path.replace("/", "_").replace("\\", "_")
        
        # Save full file content
        file_storage_path = os.path.join(files_dir, safe_path)
        with open(file_storage_path, 'w', encoding='utf-8', errors='replace') as f:
            f.write(content)
        
        # Save snippet (max 400 chars) as JSON
        snippet_data = {
            "file": file_path,
            "commit": commit_hash,
            "snippet": content[:400] if content else ""
        }
        snippet_path = os.path.join(files_dir, f"{safe_path}.snippet.json")
        with open(snippet_path, 'w', encoding='utf-8') as f:
            json.dump(snippet_data, f, indent=2)
        
        all_content += content
    
    # Calculate checksum of all content
    checksum = calculate_checksum(all_content + json.dumps(metadata_content, sort_keys=True))
    
    # Create database record
    snapshot = Snapshot(
        snapshot_id=snapshot_id,
        repo_url=repo_url,
        commit_hash=commit_hash,
        author_map=author_map,
        file_count=len(files_content),
        metadata_json=metadata_content,
        files_path=snapshot_dir,
        checksum=checksum
    )
    
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    
    return snapshot


def get_snapshot(db: Session, snapshot_id: str) -> Optional[Snapshot]:
    """Retrieve a snapshot by ID."""
    return db.query(Snapshot).filter(Snapshot.snapshot_id == snapshot_id).first()


def get_snapshot_files(snapshot_id: str) -> Dict[str, str]:
    """Retrieve stored files from a snapshot."""
    snapshot_dir = os.path.join(SNAPSHOT_STORAGE_PATH, snapshot_id)
    files_dir = os.path.join(snapshot_dir, "files")
    
    if not os.path.exists(files_dir):
        return {}
    
    files = {}
    for filename in os.listdir(files_dir):
        file_path = os.path.join(files_dir, filename)
        if os.path.isfile(file_path):
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                files[filename] = f.read()
    
    return files


def get_snapshot_metadata(snapshot_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve metadata from a snapshot."""
    metadata_path = os.path.join(SNAPSHOT_STORAGE_PATH, snapshot_id, "metadata.json")
    
    if not os.path.exists(metadata_path):
        return None
    
    with open(metadata_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def verify_snapshot_integrity(snapshot_id: str, db: Session) -> bool:
    """Verify that a snapshot has not been tampered with."""
    snapshot = get_snapshot(db, snapshot_id)
    if not snapshot:
        return False
    
    # Recalculate checksum
    files = get_snapshot_files(snapshot_id)
    metadata = get_snapshot_metadata(snapshot_id)
    
    all_content = "".join(files.values())
    current_checksum = calculate_checksum(all_content + json.dumps(metadata, sort_keys=True))
    
    return current_checksum == snapshot.checksum


def calculate_preprocessing_checksum(text_input: str) -> str:
    """
    Calculate checksum for preprocessed text input (e.g., tickets, descriptions).
    Used to ensure reproducibility of text-based evaluations.
    """
    # Normalize whitespace and lowercase for consistent checksums
    normalized = " ".join(text_input.lower().split())
    return calculate_checksum(normalized)
