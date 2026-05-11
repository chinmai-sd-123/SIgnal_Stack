"""
Scoring Engine Module.

Implements deterministic scoring per task with:
- Signal weight loading
- Raw score computation: Σ(signal * weight)
- Normalization against ALL defined weights (not just present ones)
- Authorship risk handling (soft penalty below 0.2; cap only near zero)
- Fork hard-cap (is_fork=1 and fork_is_unmodified=1 → cap at 0.3)
- Work allocation generation
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from sqlalchemy.orm import Session

from app.models.feedback import SignalWeight


@dataclass
class ScoringResult:
    """Result of scoring computation."""
    raw_score: float
    normalized_score: float
    capped_score: float
    work_allocation: float
    confidence: float
    risk_flags: List[str]
    score_breakdown: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Default signal weights (used if not in database).
#
# These weights are intentionally application-stage friendly: production hygiene
# signals such as tests, CI, Docker, and deployment readiness help, but they
# should not overwhelm evidence that a candidate actually built the thing.
DEFAULT_WEIGHTS = {
    "authorship_fraction":   0.18,
    "web_framework":         0.10,
    "valid_repo":            0.08,
    "recent_activity_score": 0.08,
    "readme_quality_score":  0.08,
    "tests_present":         0.07,
    "ci_cd_present":         0.04,   # evaluator uses ci_cd_present
    "ci_present":            0.00,   # alias handled in compute_raw_score
    "deployment_ready":      0.06,
    "dockerfile_present":    0.04,
    "migrations_present":    0.06,
    "schema_present":        0.06,
    "rate_limiting_present": 0.04,
    "commit_count":          0.04,
    # Legacy / supplementary
    "ml_model_present":      0.03,
    "ml_libraries":          0.02,
    "frontend_present":      0.04,
    "static_assets":         0.02,
}

# Sum of all default weights — used as normalization denominator
_DEFAULT_WEIGHT_SUM = sum(DEFAULT_WEIGHTS.values())

AUTHORSHIP_CAP_THRESHOLD = 0.2
VERY_LOW_AUTHORSHIP_THRESHOLD = 0.05
LOW_AUTHORSHIP_PENALTY = 0.10
MAX_SCORE_WITHOUT_AUTHORSHIP = 0.65
FORK_UNMODIFIED_CAP = 0.3


def load_signal_weights(db: Session) -> Dict[str, float]:
    """Load signal weights from DB, falling back to defaults."""
    weights = dict(DEFAULT_WEIGHTS)
    try:
        db_weights = db.query(SignalWeight).all()
        for w in db_weights:
            weights[w.signal_name] = w.weight
    except Exception:
        pass
    return weights


def _extract_value(signal_data: Any) -> float:
    """
    Safely extract a float value from either:
      - a flat float/int  (signals_map from extract_signals)
      - a structured dict {value: float, evidence: ...}  (DeterministicSignalExtractor)
    """
    if isinstance(signal_data, dict):
        return float(signal_data.get("value", 0.0))
    if isinstance(signal_data, (int, float)):
        return float(signal_data)
    return 0.0


def compute_raw_score(
    signals: Dict[str, Any],
    weights: Dict[str, float],
) -> Tuple[float, Dict[str, Any]]:
    """
    Compute raw weighted score.

    Normalises against the sum of ALL defined weights, not just the
    weights of signals that happen to be present — this prevents score
    inflation for candidates that only have a few signals.
    """
    total_score = 0.0
    breakdown: Dict[str, Any] = {}

    for signal_name, signal_data in signals.items():
        # Skip internal/meta keys
        if signal_name.startswith("_") or signal_name in ("fork_parent",):
            continue

        value = min(max(_extract_value(signal_data), 0.0), 1.0)
        weight = weights.get(signal_name, 0.0)
        if signal_name == "ci_present" and "ci_cd_present" not in signals:
            weight = weights.get("ci_cd_present", weight)
        contribution = value * weight

        breakdown[signal_name] = {
            "value": value,
            "weight": weight,
            "contribution": round(contribution, 5),
        }
        total_score += contribution

    return total_score, breakdown


def normalize_score(raw_score: float, weight_sum: float) -> float:
    """Normalize to 0–1 against the total weight sum."""
    if weight_sum <= 0:
        return 0.0
    return min(max(raw_score / weight_sum, 0.0), 1.0)


def apply_authorship_cap(
    normalized_score: float,
    signals: Dict[str, Any],
) -> Tuple[float, List[str]]:
    """
    Apply authorship-based cap only when authorship was explicitly computed.

    If authorship_fraction is absent (key missing or value == 0.0 AND
    the key was never set), we skip the cap rather than penalising
    candidates whose email we simply didn't have.

    The fork-unmodified hard cap is also applied here.
    """
    risk_flags: List[str] = []
    capped = normalized_score

    # ── Fork cap ─────────────────────────────────────────────────────────────
    is_fork = _extract_value(signals.get("is_fork", 0.0)) > 0
    fork_unmodified = _extract_value(signals.get("fork_is_unmodified", 0.0)) > 0
    if is_fork and fork_unmodified:
        risk_flags.append("fork_unmodified")
        capped = min(capped, FORK_UNMODIFIED_CAP)

    # ── Authorship cap ───────────────────────────────────────────────────────
    # Only act when the key is explicitly present (i.e. the pipeline ran the
    # authorship extractor and got a real answer, even if that answer is low).
    # Mildly low authorship is a risk flag plus soft penalty; near-zero
    # authorship remains capped because it is a stronger copied-work signal.
    if "authorship_fraction" in signals:
        authorship_fraction = _extract_value(signals["authorship_fraction"])
        if authorship_fraction < VERY_LOW_AUTHORSHIP_THRESHOLD:
            risk_flags.append("low_authorship")
            capped = min(capped, MAX_SCORE_WITHOUT_AUTHORSHIP)
        elif authorship_fraction < AUTHORSHIP_CAP_THRESHOLD:
            risk_flags.append("low_authorship")
            capped = max(0.0, capped - LOW_AUTHORSHIP_PENALTY)

    return capped, risk_flags


def compute_confidence(
    signals: Dict[str, Any],
    weights: Dict[str, float],
) -> float:
    """
    Confidence = fraction of total defined weight that is covered by
    signals with a value > 0. High coverage → high confidence.
    """
    total_defined_weight = sum(weights.values())
    covered_weight = 0.0

    for signal_name, signal_data in signals.items():
        if signal_name.startswith("_"):
            continue
        weight = weights.get(signal_name, 0.0)
        if signal_name == "ci_present" and "ci_cd_present" not in signals:
            weight = weights.get("ci_cd_present", weight)
        if weight > 0 and _extract_value(signal_data) > 0:
            covered_weight += weight

    if total_defined_weight > 0:
        return round(covered_weight / total_defined_weight, 3)
    return 0.0


def score_candidate(
    signals: Dict[str, Any],
    db: Session = None,
    weights: Dict[str, float] = None,
) -> ScoringResult:
    """
    Full scoring pipeline for a candidate.

    Accepts signals in either flat format {name: float} or structured
    format {name: {value: float, evidence: ...}}.
    """
    if weights is None:
        weights = load_signal_weights(db) if db else dict(DEFAULT_WEIGHTS)

    raw_score, breakdown = compute_raw_score(signals, weights)

    # Normalise against the full weight universe, not just present signals
    weight_sum = sum(weights.values())
    normalized_score = normalize_score(raw_score, weight_sum)

    capped_score, risk_flags = apply_authorship_cap(normalized_score, signals)

    work_allocation = round(capped_score * 100, 2)
    confidence = compute_confidence(signals, weights)

    return ScoringResult(
        raw_score=round(raw_score, 4),
        normalized_score=round(normalized_score, 4),
        capped_score=round(capped_score, 4),
        work_allocation=work_allocation,
        confidence=confidence,
        risk_flags=risk_flags,
        score_breakdown=breakdown,
    )


def generate_evaluation_trace(
    signals: Dict[str, Any],
    scoring_result: ScoringResult,
    metadata: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Generate full evaluation trace for audit storage."""
    return {
        "version": "1.1",
        "signals": {
            k: (_extract_value(v) if not isinstance(v, dict) or "value" not in v else v)
            for k, v in signals.items()
            if not k.startswith("_")
        },
        "scoring": scoring_result.to_dict(),
        "metadata": metadata or {},
    }
