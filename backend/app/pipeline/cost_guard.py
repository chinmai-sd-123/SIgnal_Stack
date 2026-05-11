"""
Cost Guard Module

Pre-evaluation checks to prevent unnecessary LLM calls.
If no valid repo is found or no evidence can be extracted,
the pipeline should stop early to save costs.
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class EligibilityResult:
    """Result of eligibility check."""
    eligible: bool
    reason: str
    details: Dict[str, Any]


def validate_eligibility(
    candidate: Dict[str, Any],
    repos: List[Dict[str, Any]],
    evidence_files: Optional[List[Dict]] = None
) -> EligibilityResult:
    """
    Check if candidate is eligible for full LLM evaluation.
    
    This is a COST GUARD: If validation fails, DO NOT call LLM.
    
    Args:
        candidate: Candidate info dict
        repos: List of selected repos (from repo_selector)
        evidence_files: Optional list of extracted evidence files
    
    Returns:
        EligibilityResult with eligible flag and reason
    """
    details = {}
    
    # Check 1: Must have at least one repo
    if not repos:
        return EligibilityResult(
            eligible=False,
            reason="NO_REPOS_FOUND",
            details={
                "candidate_id": candidate.get("id", "unknown"),
                "github_username": candidate.get("github_username", ""),
                "repo_url": candidate.get("repo_url", ""),
                "message": "No valid repositories found for candidate. Cannot proceed with evaluation."
            }
        )
    
    details["repos_found"] = len(repos)
    
    # Check 2: At least one repo should have a manifest
    has_manifest = any(r.get("manifest_present", False) if isinstance(r, dict) else getattr(r, "manifest_present", False) for r in repos)
    details["has_manifest"] = has_manifest
    
    if not has_manifest:
        # Warning but not blocking - some repos might be valid without manifest
        details["warning"] = "No manifest files detected in any repo. Evaluation may be limited."
    
    # Check 3: Evidence files (if provided)
    if evidence_files is not None:
        if not evidence_files:
            return EligibilityResult(
                eligible=False,
                reason="NO_EVIDENCE_EXTRACTED",
                details={
                    **details,
                    "message": "No evidence files could be extracted from repositories."
                }
            )
        details["evidence_count"] = len(evidence_files)
    
    # Check 4: Repo scores (if available) - warn if all scores are very low
    if repos:
        scores = []
        for r in repos:
            score = r.get("score", 0.5) if isinstance(r, dict) else getattr(r, "score", 0.5)
            scores.append(score)
        avg_score = sum(scores) / len(scores) if scores else 0
        details["avg_repo_score"] = round(avg_score, 3)
        
        if avg_score < 0.2:
            details["warning"] = "All selected repos have very low relevance scores."
    
    return EligibilityResult(
        eligible=True,
        reason="ELIGIBLE",
        details=details
    )


def should_skip_llm(eligibility: EligibilityResult) -> Tuple[bool, str]:
    """
    Determine if LLM call should be skipped based on eligibility.
    
    Returns:
        (should_skip, reason) tuple
    """
    if not eligibility.eligible:
        return (True, eligibility.reason)
    
    return (False, "")


def create_fallback_evaluation(
    candidate: Dict[str, Any],
    reason: str,
    details: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create a minimal evaluation result when LLM is skipped.
    
    This provides a deterministic fallback instead of calling LLM.
    """
    return {
        "candidate_id": candidate.get("id", "unknown"),
        "skipped": True,
        "skip_reason": reason,
        "fit_score": 0.0,
        "health_score": 0.0,
        "confidence": 0.0,
        "signals": {},
        "risk_flags": [reason],
        "task_scores": {},
        "llm_called": False,
        "message": details.get("message", "Evaluation skipped due to missing prerequisites."),
        "details": details
    }
