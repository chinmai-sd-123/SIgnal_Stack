import pytest

import app.schemas as schemas
from app.pipeline.evaluator import (
    _accumulate_dimensions,
    _average_dimension_accumulator,
    _candidate_fit_score,
    _candidate_quality,
    Evaluator,
)
from app.schemas.evaluation import CandidateScore
from app.schemas.proof import Evidence


@pytest.mark.unit
def test_candidate_quality_separates_capability_from_verification():
    quality = _candidate_quality(
        {
            "authorship_fraction": 0.1,
            "valid_repo": 1.0,
            "web_framework": 1.0,
            "recent_activity_score": 1.0,
            "readme_quality_score": 0.6,
            "tests_present": 0.0,
            "ci_cd_present": 0.0,
        },
        capability_score=0.82,
    )

    assert quality["capability_score"] == 0.82
    assert quality["verification_status"] == "unverified"
    assert "low_authorship" in quality["risk_flags"]
    assert quality["production_readiness"] < 0.5


@pytest.mark.unit
def test_candidate_quality_flags_unmodified_fork_as_conflict():
    quality = _candidate_quality(
        {
            "authorship_fraction": 0.8,
            "is_fork": 1.0,
            "fork_is_unmodified": 1.0,
            "tests_present": 1.0,
            "ci_cd_present": 1.0,
        },
        capability_score=0.9,
    )

    assert quality["verification_status"] == "conflict"
    assert "fork_unmodified" in quality["risk_flags"]
    assert quality["confidence_rating"] == "Low"


@pytest.mark.unit
def test_candidate_fit_score_uses_same_blend_as_report_fit():
    quality = _candidate_quality(
        {
            "authorship_fraction": 1.0,
            "valid_repo": 1.0,
            "recent_activity_score": 1.0,
            "readme_quality_score": 1.0,
            "tests_present": 1.0,
            "ci_cd_present": 1.0,
            "deployment_ready": 1.0,
        },
        capability_score=0.48,
    )

    fit_score = _candidate_fit_score(0.48, quality)

    assert fit_score > 0.48
    assert fit_score == round(0.48 * 0.75 + quality["scoring"].capped_score * 0.25, 3)


@pytest.mark.unit
def test_candidate_score_can_carry_candidate_specific_evidence():
    score = CandidateScore(
        candidate_id="candidate-b",
        score=0.62,
        justification="Relevant implementation found.",
        evidence=[
            Evidence(
                type="code_snippet",
                ref="FILE:candidate_b/app.py",
                snippet="candidate b implementation",
                source_url="https://github.com/candidate-b/repo/blob/main/app.py",
            )
        ],
    )

    dumped = score.model_dump()

    assert dumped["evidence"][0]["ref"] == "FILE:candidate_b/app.py"
    assert "candidate-b/repo" in dumped["evidence"][0]["source_url"]


@pytest.mark.unit
def test_dimension_accumulator_averages_multiple_task_scores():
    accumulator = None
    accumulator = _accumulate_dimensions(
        accumulator,
        {
            "project_completion": 8,
            "engineering_quality": 6,
            "communication": 4,
            "innovation": 5,
            "depth_novelty": 7,
        },
    )
    accumulator = _accumulate_dimensions(
        accumulator,
        {
            "project_completion": 4,
            "engineering_quality": 8,
            "communication": 6,
            "innovation": 7,
            "depth_novelty": 5,
        },
    )

    averaged = _average_dimension_accumulator(accumulator)

    assert averaged == {
        "project_completion": 6.0,
        "engineering_quality": 7.0,
        "communication": 5.0,
        "innovation": 6.0,
        "depth_novelty": 6.0,
    }


@pytest.mark.unit
def test_task_context_includes_outcome_and_signal_text():
    class Outcome:
        title = "AI Health Monitoring"
        description = "Evaluate health risk prediction projects"

    class Task:
        name = "Train baseline model and report F1 score"

    context = Evaluator()._build_task_context(Outcome(), Task())

    assert "Outcome: AI Health Monitoring" in context
    assert "Outcome Description: Evaluate health risk prediction projects" in context
    assert "Signal: Train baseline model and report F1 score" in context


@pytest.mark.unit
def test_batched_evaluator_uses_one_llm_call_per_candidate_outcome(monkeypatch):
    calls = []

    class Outcome:
        id = "outcome-1"
        job_id = "job-1"
        title = "Build AI workflow"
        description = "Candidate can ship an AI workflow."

    class Task:
        def __init__(self, task_id, name):
            self.id = task_id
            self.name = name
            self.priority = "High"
            self.weight = 0.5

    outcome = Outcome()
    outcome.tasks = [
        Task("task-1", "Send code to an LLM service"),
        Task("task-2", "Render review feedback to the user"),
    ]

    class FakeExtractor:
        def extract_evidence(self, **kwargs):
            return [
                Evidence(
                    type="code_snippet",
                    ref="FILE:app/main.py",
                    snippet="def review_code(code):\n    return llm.review(code)",
                )
            ]

        def extract_authorship_signals(self, *args, **kwargs):
            return Evidence(
                type="authorship_context",
                ref="AUTHORSHIP",
                snippet="Authorship confirmed.",
            )

    class FakeLLM:
        def interpret_outcome_signals(self, outcome_description, task_evidence, payload=None, tracking_context=None):
            calls.append({
                "outcome_description": outcome_description,
                "task_evidence": task_evidence,
                "tracking_context": tracking_context,
            })
            return {
                item["task_id"]: {
                    "strength": 0.7,
                    "justification": f"Relevant implementation for {item['task_name']}",
                    "relevant_evidence": "FILE:app/main.py\nreview_code",
                    "dimensions": {
                        "project_completion": 7,
                        "engineering_quality": 7,
                        "communication": 6,
                        "innovation": 6,
                        "depth_novelty": 6,
                    },
                }
                for item in task_evidence
            }

    monkeypatch.setattr("app.services.llm.OpenAILLMService", lambda: FakeLLM())

    evaluator = Evaluator()
    evaluator.extractor = FakeExtractor()
    proof = schemas.ProofCreate(
        job_id="outcome-1",
        candidate_id="candidate@example.com",
        type="github",
        payload={
            "repo_url": "https://github.com/acme/reviewer",
            "candidate_email": "candidate@example.com",
        },
    )

    result = evaluator.evaluate_batched(
        outcome,
        [proof],
        {
            "candidate@example.com": {
                "authorship_fraction": 1.0,
                "tests_present": 1.0,
                "readme_quality_score": 1.0,
            }
        },
    )

    assert len(calls) == 1
    assert len(calls[0]["task_evidence"]) == 2
    assert calls[0]["tracking_context"]["operation"] == "outcome_signal_interpretation"
    assert len(result.work_allocation) == 2
    assert result.candidate_summaries[0].candidate_id == "candidate@example.com"
    assert result.fit_score == result.candidate_summaries[0].overall_score
    assert result.candidate_summaries[0].overall_score != result.candidate_summaries[0].capability_score
    assert result.candidate_summaries[0].tasks_won == 2
