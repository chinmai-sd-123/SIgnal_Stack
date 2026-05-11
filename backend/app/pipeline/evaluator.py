from typing import List, Dict
import app.schemas as schemas
from app.pipeline.matcher import Matcher
from app.pipeline.allocator import Allocator
from app.pipeline.signal_extractor import SignalExtractor
from app.pipeline.cost_guard import validate_eligibility, should_skip_llm, create_fallback_evaluation
from app.services.leetcode import LeetCodeService


class Evaluator:
    def __init__(self):
        self.matcher = Matcher()
        self.allocator = Allocator()
        self.extractor = SignalExtractor()
        self.leetcode_service = LeetCodeService()

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
                    print(f"DEBUG: Skipping {cand_id} - No evidence provided.")
                    continue
                
                # Safe Clean URL for display
                display_url = repo_url or artifact_link or ""
                clean_repo_url = display_url.rstrip('/')
                if clean_repo_url.endswith('.git'):
                    clean_repo_url = clean_repo_url[:-4]

                print(f"DEBUG: Extracting evidence for {task.name}. Candidate: {cand_id}")

                # Extract evidence specific to this task
                task_evidence = self.extractor.extract_evidence(
                    repo_url=repo_url, 
                    task_title=task.name,
                    context=context_desc,
                    artifact_link=artifact_link
                )
                print(f"DEBUG: Evidence found: {len(task_evidence)}")
                
                # GitHub-specific checks
                if repo_url and "github.com" in repo_url:
                    # Forensic Authorship Check (Task-Specific)
                    authorship_evidence = self.extractor.extract_authorship_signals(repo_url, cand_id, task.name)
                    task_evidence.append(authorship_evidence)
                    
                    # Inject Phase 1 Signals (Heuristic Project Health)
                    cand_signals = signals_map.get(cand_id, {})
                    if cand_signals:
                        task_short = task.name[:30].replace(' ', '_') if task.name else 'general'
                        sig_snippet = f"Task: {task.name}\n\nProject Health Signals (Phase 1 Analysis):\n"
                        sig_keys = ["tests_present", "ci_cd_present", "deployment_ready", "ml_model_present", "commit_count", "unique_authors"]
                        for k in sig_keys:
                            val = cand_signals.get(k, 0)
                            label = k.replace('_', ' ').title()
                            status = "YES" if val > 0 else "NO"
                            if isinstance(val, int) and val > 1: status = str(val)
                            sig_snippet += f"- {label}: {status}\n"
                        
                        task_evidence.append(schemas.Evidence(
                            type="heuristic_context",
                            ref=f"SCAN:{task_short}",
                            snippet=sig_snippet,
                            source_url=f"{clean_repo_url}#signals"
                        ))

                    # LeetCode Stats Injection
                    leetcode_user = proof.payload.get("leetcode_username")
                    if leetcode_user:
                        stats = self.leetcode_service.fetch_stats(leetcode_user)
                        if "error" not in stats:
                            stats_snippet = f"LeetCode Profile: {leetcode_user}\n"
                            stats_snippet += f"Total Solved: {stats.get('total_solved')} (Easy: {stats.get('easy_solved')}, Med: {stats.get('medium_solved')}, Hard: {stats.get('hard_solved')})\n"
                            stats_snippet += f"Acceptance Rate: {stats.get('acceptance_rate')}%\n"
                            stats_snippet += f"Ranking: {stats.get('ranking')}"
                            
                            task_evidence.append(schemas.Evidence(
                                type="leetcode_stats",
                                ref="LEETCODE",
                                snippet=stats_snippet,
                                source_url=f"https://leetcode.com/{leetcode_user}"
                            ))

                # 2. LLM Interpretation
                # Sort evidence for deterministic LLM input
                task_evidence.sort(key=lambda e: e.ref.lower())
                evidence_dicts = [e.dict() for e in task_evidence]
                interpretation = llm.interpret_signals(
                    task.description if hasattr(task, 'description') else task.name, 
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
                if dims and not candidate_stats[cand_id]['dimensions']:
                    candidate_stats[cand_id]['dimensions'] = dims
                
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
                    justification=cs['justification']
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
        
        for alloc in allocations:
            task_obj = next((t for t in outcome.tasks if t.name == alloc.task_title), None)
            weight = task_obj.weight if task_obj else 0.0
            
            # Sum up contributions
            total_fit += (alloc.confidence * weight)
            total_possible_weight += weight

        # NORMALIZE: Ensure score is relative to total weight sum
        if total_possible_weight > 0:
            final_score = total_fit / total_possible_weight
        else:
            final_score = 0.0

        # NEW: Build candidate summaries
        candidate_summaries = []
        all_scores = [cs['total_score'] / max(cs['task_count'], 1) for cs in candidate_stats.values() if cs['task_count'] > 0]
        max_score = max(all_scores) if all_scores else 0
        
        for cand_id, stats in candidate_stats.items():
            if stats['task_count'] == 0:
                continue
            
            avg_score = stats['total_score'] / stats['task_count']
            
            # Calculate confidence rating based on score differential
            if max_score > 0:
                score_ratio = avg_score / max_score
                if score_ratio >= 0.9:
                    confidence = "High"
                elif score_ratio >= 0.7:
                    confidence = "Medium"
                else:
                    confidence = "Low"
            else:
                confidence = "Low"
            
            candidate_summaries.append(schemas.CandidateSummary(
                candidate_id=cand_id,
                overall_score=round(avg_score, 2),
                tasks_won=stats['wins'],
                dimensions=stats['dimensions'],
                confidence_rating=confidence
            ))
        
        # Sort summaries by overall_score descending
        candidate_summaries.sort(key=lambda x: x.overall_score, reverse=True)

        return schemas.EvaluationResponse(
            job_id=outcome.id,
            job_title=None,  # Injected by route handler
            fit_score=round(final_score, 2),
            work_allocation=allocations,
            global_signals_used=sorted(list(global_signals_used)),
            risk_flags=[],
            human_action_required=True,
            dimensions=candidate_summaries[0].dimensions if candidate_summaries else None,
            candidate_summaries=candidate_summaries
        )
