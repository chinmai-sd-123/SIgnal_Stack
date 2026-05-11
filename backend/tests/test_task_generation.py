import json

import pytest

from app.services.llm import OpenAILLMService


@pytest.mark.unit
def test_task_generation_fallback_prefers_artifact_verifiable_signals():
    service = OpenAILLMService()
    service.api_key = ""
    service.client = None

    tasks = service.generate_tasks(
        "Outcome Title: Build AI Code Review Workflow\n"
        "Outcome Goal: users submit code and receive AI-generated review feedback"
    )

    assert 3 <= len(tasks) <= 5
    assert all(len(task["name"]) <= 140 for task in tasks)
    assert not all(task["priority"] == "High" for task in tasks)
    assert any("workflow" in task["name"].lower() or "llm" in task["name"].lower() for task in tasks)


@pytest.mark.unit
def test_task_generation_cleans_llm_output(monkeypatch):
    service = OpenAILLMService()
    service.api_key = "test-key"
    service.client = object()
    long_name = " ".join(["Build"] * 50)

    monkeypatch.setattr(
        service,
        "_call_with_retry",
        lambda prompt, schema: json.dumps({
            "tasks": [
                {"name": long_name, "priority": "High"},
                {"name": "Sends submitted code or repository context to an LLM review service", "priority": "High"},
                {"name": "Sends submitted code or repository context to an LLM review service", "priority": "High"},
                {"name": "Shows generated review feedback with bugs, improvements, and readability suggestions", "priority": "High"},
                {"name": "Handles loading, success, and error states during review generation", "priority": "High"},
            ]
        }),
    )

    tasks = service.generate_tasks("Outcome Goal: Build an AI code reviewer")

    assert 3 <= len(tasks) <= 5
    assert all(len(task["name"]) <= 140 for task in tasks)
    assert len({task["name"] for task in tasks}) == len(tasks)
    assert any(task["priority"] == "Medium" for task in tasks)
