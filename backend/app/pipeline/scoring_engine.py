"""
Scoring Engine Module.

Implements deterministic scoring per task with:
- Signal weight loading
- Raw score computation: Σ(signal * weight)
- Normalization
- Authorship capping (if authorship < 0.2, cap score at 0.2)
- Work allocation generation
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from sqlalchemy.orm import Session

from app.models.feedback import SignalWeight
from app.models.snapshot import SignalWeightHistory


@dataclass
class ScoringResult:
    """Result of scoring computation."""
    raw_score: float
    normalized_score: float
    capped_score: float
    work_allocation: float
    confidence: float
    risk_flags: List[str]
    score_breakdown: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Default signal weights (used if not in database)
DEFAULT_WEIGHTS = {
    "authorship_fraction": 0.25,
    "tests_present": 0.15,
    "ci_present": 0.10,
    "dockerfile_present": 0.10,
    "schema_present": 0.10,
    "rate_limiting_present": 0.05,
    "readme_quality_score": 0.10,
    # Legacy signals for backward compatibility
    "valid_repo": 0.05,
    "ml_model_present": 0.05,
    "deployment_ready": 0.05,
}

# Minimum authorship threshold
AUTHORSHIP_CAP_THRESHOLD = 0.2
MAX_SCORE_WITHOUT_AUTHORSHIP = 0.2


def load_signal_weights(db: Session) -> Dict[str, float]:
    """
    Load signal weights from database.
    Falls back to defaults if not configured.
    """
    weights = dict(DEFAULT_WEIGHTS)
    
    try:
        db_weights = db.query(SignalWeight).all()
        for w in db_weights:
            weights[w.signal_name] = w.weight
    except Exception:
        pass  # Use defaults if DB query fails
    
    return weights


def compute_raw_score(
    signals: Dict[str, Dict[str, Any]],
    weights: Dict[str, float]
) -> tuple[float, Dict[str, float]]:
    """
    Compute raw weighted score.
    
    Args:
        signals: {signal_name: {name, value, evidence}}
        weights: {signal_name: weight}
    
    Returns:
        (raw_score, score_breakdown)
    """
    total_score = 0.0
    breakdown = {}
    
    for signal_name, signal_data in signals.items():
        val_raw = signal_data.get("value", 0.0) if isinstance(signal_data, dict) else 0.0
        # Clamp value to 1.0 to prevent score inflation > 100%
        value = min(max(val_raw, 0.0), 1.0)
        
        weight = weights.get(signal_name, 0.0)
        contribution = value * weight
        
        breakdown[signal_name] = {
            "value": value,
            "weight": weight,
            "contribution": contribution
        }
        total_score += contribution
    
    return total_score, breakdown


def normalize_score(raw_score: float, max_possible: float = 1.0) -> float:
    """
    Normalize score to 0-1 range.
    """
    if max_possible <= 0:
        return 0.0
    return min(max(raw_score / max_possible, 0.0), 1.0)


def apply_authorship_cap(
    normalized_score: float,
    authorship_fraction: float
) -> tuple[float, List[str]]:
    """
    Apply authorship-based capping.
    
    If authorship < 0.2, cap the final score at 0.2.
    
    Returns:
        (capped_score, risk_flags)
    """
    risk_flags = []
    
    if authorship_fraction < AUTHORSHIP_CAP_THRESHOLD:
        risk_flags.append("low_authorship")
        capped_score = min(normalized_score, MAX_SCORE_WITHOUT_AUTHORSHIP)
        return capped_score, risk_flags
    
    return normalized_score, risk_flags


def compute_work_allocation(capped_score: float) -> float:
    """
    Compute recommended work allocation percentage.
    
    Higher scores = more work allocation (in multi-candidate scenarios).
    """
    # Simple linear mapping for now
    # Could be enhanced with more sophisticated allocation algorithms
    return round(capped_score * 100, 2)


def compute_confidence(
    signals: Dict[str, Dict[str, Any]],
    weights: Dict[str, float]
) -> float:
    """
    Compute confidence score based on signal coverage.
    
    High confidence = more signals present with evidence.
    """
    present_signals = 0
    total_weight = 0.0
    covered_weight = 0.0
    
    for signal_name, signal_data in signals.items():
        weight = weights.get(signal_name, 0.0)
        if weight > 0:
            total_weight += weight
            value = signal_data.get("value", 0.0) if isinstance(signal_data, dict) else 0.0
            if value > 0:
                present_signals += 1
                covered_weight += weight
    
    if total_weight > 0:
        return round(covered_weight / total_weight, 2)
    return 0.0


def score_candidate(
    signals: Dict[str, Dict[str, Any]],
    db: Session = None,
    weights: Dict[str, float] = None
) -> ScoringResult:
    """
    Full scoring pipeline for a candidate.
    
    Args:
        signals: Dictionary of signals (from deterministic_signals module)
        db: Database session for loading weights
        weights: Optional pre-loaded weights (overrides DB)
    
    Returns:
        ScoringResult with all scoring details
    """
    # Load weights
    if weights is None:
        if db:
            weights = load_signal_weights(db)
        else:
            weights = DEFAULT_WEIGHTS
    
    # Compute raw score
    raw_score, breakdown = compute_raw_score(signals, weights)
    
    # Calculate max possible score
    max_possible = sum(weights.get(s, 0.0) for s in signals.keys())
    
    # Normalize
    normalized_score = normalize_score(raw_score, max_possible)
    
    # Get authorship fraction for capping
    authorship_data = signals.get("authorship_fraction", {})
    authorship_fraction = authorship_data.get("value", 0.0) if isinstance(authorship_data, dict) else 0.0
    
    # Apply authorship cap
    capped_score, risk_flags = apply_authorship_cap(normalized_score, authorship_fraction)
    
    # Compute work allocation
    work_allocation = compute_work_allocation(capped_score)
    
    # Compute confidence
    confidence = compute_confidence(signals, weights)
    
    return ScoringResult(
        raw_score=round(raw_score, 4),
        normalized_score=round(normalized_score, 4),
        capped_score=round(capped_score, 4),
        work_allocation=work_allocation,
        confidence=confidence,
        risk_flags=risk_flags,
        score_breakdown=breakdown
    )


def generate_evaluation_trace(
    signals: Dict[str, Dict[str, Any]],
    scoring_result: ScoringResult,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Generate complete evaluation trace for audit.
    
    This is stored in evaluations.evaluation_json for full reproducibility.
    """
    return {
        "version": "1.0",
        "signals": signals,
        "scoring": scoring_result.to_dict(),
        "metadata": metadata or {},
    }
