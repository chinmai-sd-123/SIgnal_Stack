import logging
from typing import List, Dict

from app.models import feedback
import app.schemas as schemas
from app.pipeline.matcher import Matcher
from app.pipeline.allocator import Allocator
from app.pipeline.signal_extractor import SignalExtractor
from app.pipeline.cost_guard import validate_eligibility, should_skip_llm, create_fallback_evaluation
from app.pipeline.scoring_engine import score_candidate


logger = logging.getLogger(__name__)

def _avg_dimensions(summaries: List) -> Dict:
    """Average dimension scores across all evaluated candidates."""
    dim_totals = {}
    count = 0
    for s in summaries:
        if s.dimensions:
            count += 1
            for k, v in s.dimensions.items():
                dim_totals[k] = dim_totals.get(k, 0.0) + v
    if count == 0:
        return None
    return {k: round(v / count, 2) for k, v in dim_totals.items()}


def _accumulate_dimensions(current: Dict, dims: Dict) -> Dict:
    """Accumulate task-level dimension scores for later averaging."""
    if not dims:
        return current

    if current is None:
        current = {"totals": {}, "count": 0}

    current["count"] += 1
    for key, value in dims.items():
        try:
            current["totals"][key] = current["totals"].get(key, 0.0) + float(value or 0.0)
        except (TypeError, ValueError):
            current["totals"][key] = current["totals"].get(key, 0.0)
    return current


def _average_dimension_accumulator(accumulator: Dict) -> Dict:
    """Convert accumulated task dimensions into radar-chart values."""
    if not accumulator or accumulator.get("count", 0) <= 0:
        return None
    count = accumulator["count"]
    return {
        key: round(value / count, 2)
        for key, value in accumulator.get("totals", {}).items()
    }


def _production_readiness(signals: Dict) -> float:
    """Score production hygiene separately from capability."""
    checks = {
        "tests_present": 0.25,
        "ci_cd_present": 0.15,
        "deployment_ready": 0.15,
        "dockerfile_present": 0.10,
        "readme_quality_score": 0.15,
        "rate_limiting_present": 0.10,
        "migrations_present": 0.10,
    }
    total = sum(checks.values())
    if total <= 0:
        return 0.0

    score = 0.0
    for key, weight in checks.items():
        value = signals.get(key, 0.0)
        if isinstance(value, dict):
            value = value.get("value", 0.0)
        if key == "readme_quality_score":
            score += min(max(float(value or 0.0), 0.0), 1.0) * weight
        elif float(value or 0.0) > 0:
            score += weight
    return round(score / total, 3)


def _verification_status(signals: Dict, risk_flags: List[str]) -> str:
    """Expose authorship as trust state, not the core capability score."""
    if "fork_unmodified" in risk_flags:
        return "conflict"
    if "authorship_fraction" not in signals:
        return "unverified"

    value = signals.get("authorship_fraction", 0.0)
    if isinstance(value, dict):
        value = value.get("value", 0.0)
    authorship_fraction = float(value or 0.0)
    if authorship_fraction >= 0.2:
        return "verified"
    if authorship_fraction < 0.05:
        return "conflict"
    return "unverified"


def _confidence_rating(capability: float, evidence_confidence: float, verification_status: str) -> str:
    if verification_status == "conflict":
        return "Low"
    combined = capability * 0.7 + evidence_confidence * 0.3
    if combined >= 0.75:
        return "High"
    if combined >= 0.45:
        return "Medium"
    return "Low"


def _candidate_quality(signals: Dict, capability_score: float) -> Dict:
    scoring = score_candidate(signals) if signals else None
    risk_flags = scoring.risk_flags if scoring else []
    evidence_confidence = scoring.confidence if scoring else 0.0
    production_readiness = _production_readiness(signals or {})
    verification_status = _verification_status(signals or {}, risk_flags)
    return {
        "capability_score": round(capability_score, 2),
        "evidence_confidence": round(evidence_confidence, 2),
        "production_readiness": round(production_readiness, 2),
        "verification_status": verification_status,
        "confidence_rating": _confidence_rating(capability_score, evidence_confidence, verification_status),
        "risk_flags": sorted(risk_flags),
        "scoring": scoring,
    }

class Evaluator:
    def __init__(self):
        self.matcher = Matcher()
        self.allocator = Allocator()
        self.extractor = SignalExtractor()

    def evaluate(self, outcome: schemas.OutcomeCreate, proofs: List[schemas.ProofCreate], signals_map: Dict[str, Dict]) -> schemas.EvaluationResponse:
        """
        Evaluate all candidates (proofs) against all tasks in the outcome.
        For each task, find the best matching candidate and track all scores.
        """
        allocations = []
        global_signals_used = set()
        
        # NEW: Track per-candidate stats for summary
        candidate_stats = {}  # {cand_id: {total_score, task_count, wins, dimensions}}
        
        from app.services.llm import OpenAILLMService
        llm = OpenAILLMService()
        
        # For each task, evaluate all candidates and pick the best
        for task in outcome.tasks:
            task_context = self._build_task_context(outcome, task)
            best_candidate = None
            best_score = 0.0
            best_reasons = []
            best_evidence = []
            
            # NEW: Track all candidate scores for this task
            task_candidate_scores = []
            
            # Evaluate each candidate (proof) for this task
            for proof in proofs:
                cand_id = proof.candidate_id
                
                # Initialize candidate stats if not exists
                if cand_id not in candidate_stats:
                    candidate_stats[cand_id] = {
                        'total_score': 0.0,
                        'task_count': 0,
                        'wins': 0,
                        'dimensions': None
                    }
                
                # 1. Signal Extraction (Gather Evidence)
                repo_url = proof.payload.get("repo_url", "")
                artifact_link = proof.payload.get("artifact_link")
                context_desc = proof.payload.get("context", "")
                
                # Skip candidates without evidence
                if not repo_url and not artifact_link:
                    logger.debug("Skipping %s - No evidence provided.", cand_id)
                    continue
                
                # Safe Clean URL for display
                display_url = repo_url or artifact_link or ""
                clean_repo_url = display_url.rstrip('/')
                if clean_repo_url.endswith('.git'):
                    clean_repo_url = clean_repo_url[:-4]

                logger.debug("Extracting evidence for %s. Candidate: %s", task.name, cand_id)

                # Extract evidence specific to this task
                task_evidence = self.extractor.extract_evidence(
                    repo_url=repo_url, 
                    task_title=task_context,
                    context=context_desc,
                    artifact_link=artifact_link
                )
                logger.debug("Evidence found: %s", len(task_evidence))
                task_short = task.name[:30].replace(' ', '_') if task.name else 'general'
                # GitHub-specific checks
                if repo_url and "github.com" in repo_url:
                    # Forensic Authorship Check (Task-Specific)
                    authorship_evidence = self.extractor.extract_authorship_signals(
                        repo_url,
                        cand_id,
                        task_context,
                        candidate_info=proof.payload,                              # ← identity fields
                        cached_author_map=signals_map.get(cand_id, {}).get("_author_map"),  # ← skip re-fetch
                    )
                    task_evidence.append(authorship_evidence)
                    
                    # Inject Phase 1 Signals (Heuristic Project Health)
                    cand_signals = signals_map.get(cand_id, {})
                    if cand_signals:
                        sig_snippet = f"Task: {task.name}\n\nProject Health Signals (Phase 1 Analysis):\n"
                        sig_keys = [
                            "tests_present", "ci_cd_present", "deployment_ready",
                            "ml_model_present", "commit_count", "unique_authors",
                            "recent_activity_score", "is_fork", "fork_is_unmodified",
                            "readme_quality_score", "rate_limiting_present",
                        ]
                        for k in sig_keys:
                            val = cand_signals.get(k, 0)
                            label = k.replace('_', ' ').title()
                            # Boolean signals → YES/NO; numeric signals → their value
                            if k in ("commit_count", "unique_authors", "recent_activity_score", "readme_quality_score"):
                                status = str(round(val, 3)) if isinstance(val, float) else str(val)
                            else:
                                status = "YES" if val > 0 else "NO"
                            sig_snippet += f"- {label}: {status}\n"
                        
                        task_evidence.append(schemas.Evidence(
                            type="heuristic_context",
                            ref=f"SCAN:{task_short}",
                            snippet=sig_snippet,
                            source_url=f"{clean_repo_url}#signals"
                        ))

                # 2. LLM Interpretation
                # Keep extractor priority order so task-specific implementation
                # snippets reach the LLM before generic manifests or README.
                evidence_dicts = [e.model_dump() for e in task_evidence]
                interpretation = llm.interpret_signals(
                    task_context,
                    evidence_dicts,
                    payload=proof.payload
                )
                
                signal_strength = interpretation.get("strength", 0.0)
                justification = interpretation.get("justification", "No justification provided.")
                relevant_evidence_text = interpretation.get("relevant_evidence", "")
                dims = interpretation.get("dimensions")
                
                # Add the LLM's key finding as a synthesized evidence item
                if relevant_evidence_text and relevant_evidence_text not in ("None", "Error", ""):
                    task_evidence.insert(0, schemas.Evidence(
                        type="code_snippet",
                        ref=f"AI_FINDING:{task_short}",
                        snippet=f"Key Evidence (AI Analysis):\n{relevant_evidence_text}",
                        source_url=clean_repo_url if repo_url else None
                    ))
                
                # 3. Deterministic Scoring
                score = self.matcher.calculate_task_score(signal_strength)
                
                # NEW: Store this candidate's score for this task
                task_candidate_scores.append({
                    'candidate_id': cand_id,
                    'score': round(score, 2),
                    'justification': justification,
                    'evidence': task_evidence,
                    'dimensions': dims
                })
                
                # Update candidate stats
                candidate_stats[cand_id]['total_score'] += score
                candidate_stats[cand_id]['task_count'] += 1
                if dims:
                    candidate_stats[cand_id]['dimensions'] = _accumulate_dimensions(
                        candidate_stats[cand_id]['dimensions'],
                        dims,
                    )
                
                # Track best candidate for this task
                if score > best_score:
                    best_score = score
                    best_candidate = cand_id
                    best_reasons = [justification]
                    best_evidence = task_evidence
                    
                    # Add pseudo-signals for usage tracking
                    if score > 0.5:
                        global_signals_used.add(f"verified_{task.name.replace(' ', '_').lower()}")

            # Mark the winner for this task
            if best_candidate:
                candidate_stats[best_candidate]['wins'] += 1
            
            # Sort task scores for ranking (highest first)
            task_candidate_scores.sort(key=lambda x: x['score'], reverse=True)
            
            # Create top_candidates list for this allocation
            top_candidates = [
                schemas.CandidateScore(
                    candidate_id=cs['candidate_id'],
                    score=cs['score'],
                    justification=cs['justification'],
                    evidence=cs.get('evidence') or []
                )
                for cs in task_candidate_scores[:5]  # Top 5 candidates per task
            ]
            
            # Create allocation for this task with best candidate
            alloc = self.allocator.create_allocation(
                task, best_candidate, best_score, best_reasons, best_evidence
            )
            alloc.top_candidates = top_candidates
            allocations.append(alloc)

        # Calculate overall fit score (Weighted Average)
        total_fit = 0.0
        total_possible_weight = 0.0
        all_risk_flags: List[str] = []

        for alloc in allocations:
            task_obj = next((t for t in outcome.tasks if t.name == alloc.task_title), None)
            weight = task_obj.weight if task_obj else 0.0
            total_fit += (alloc.confidence * weight)
            total_possible_weight += weight

        if total_possible_weight > 0:
            raw_final = total_fit / total_possible_weight
        else:
            raw_final = 0.0

        # NEW: Build candidate summaries
        candidate_summaries = []
        
        for cand_id, stats in candidate_stats.items():
            if stats['task_count'] == 0:
                continue
            
            avg_score = stats['total_score'] / stats['task_count']
            
            quality = _candidate_quality(signals_map.get(cand_id, {}), avg_score)
            
            candidate_summaries.append(schemas.CandidateSummary(
                candidate_id=cand_id,
                overall_score=round(avg_score, 2),
                capability_score=quality["capability_score"],
                evidence_confidence=quality["evidence_confidence"],
                production_readiness=quality["production_readiness"],
                verification_status=quality["verification_status"],
                tasks_won=stats['wins'],
                dimensions=_average_dimension_accumulator(stats['dimensions']),
                confidence_rating=quality["confidence_rating"],
                risk_flags=quality["risk_flags"],
            ))
        
        # Sort summaries by overall_score descending
        candidate_summaries.sort(key=lambda x: x.overall_score, reverse=True)

        # Run the top candidate's signals through the scoring engine for
        # authoritative capping + risk flags, then blend with LLM scores.
        top_candidate_id = candidate_summaries[0].candidate_id if candidate_summaries else None
        top_quality = None
        if top_candidate_id and top_candidate_id in signals_map:
            top_signals = signals_map[top_candidate_id]
            top_capability = candidate_summaries[0].capability_score or raw_final
            top_quality = _candidate_quality(top_signals, top_capability)
            scoring = top_quality["scoring"]
            all_risk_flags = scoring.risk_flags
            # Let direct task evidence lead for early applications. Deterministic
            # project-health signals still matter, but missing tests/CI should
            # not overpower a relevant working implementation.
            final_score = round(raw_final * 0.75 + scoring.capped_score * 0.25, 3)
        else:
            final_score = round(raw_final, 3)
            top_quality = {
                "capability_score": round(raw_final, 2),
                "evidence_confidence": 0.0,
                "production_readiness": 0.0,
                "verification_status": "unverified",
            }

        return schemas.EvaluationResponse(
            job_id=outcome.id,
            job_title=None,  # Injected by route handler
            fit_score=round(final_score, 2),
            capability_score=top_quality["capability_score"],
            evidence_confidence=top_quality["evidence_confidence"],
            production_readiness=top_quality["production_readiness"],
            verification_status=top_quality["verification_status"],
            work_allocation=allocations,
            global_signals_used=sorted(list(global_signals_used)),
            risk_flags=sorted(all_risk_flags) if all_risk_flags else [],
            human_action_required=True,
            dimensions=_avg_dimensions(candidate_summaries),
            candidate_summaries=candidate_summaries
        )

    def _build_task_context(self, outcome, task) -> str:
        """Combine outcome and task text so signal extraction has domain context."""
        parts = []
        if getattr(outcome, "title", None):
            parts.append(f"Outcome: {outcome.title}")
        if getattr(outcome, "description", None):
            parts.append(f"Outcome Description: {outcome.description}")
        if getattr(task, "name", None):
            parts.append(f"Signal: {task.name}")
        return "\n".join(parts) or getattr(task, "name", "")
