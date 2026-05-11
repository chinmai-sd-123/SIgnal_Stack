import pytest

from app.services.llm import OpenAILLMService


@pytest.mark.unit
def test_relevant_evidence_must_be_grounded_in_source_snippets():
    service = OpenAILLMService()
    evidence = [
        {
            "type": "code_snippet",
            "ref": "FILE:app/main.py",
            "snippet": "async def webhook(request):\n    body = await request.json()\n",
        }
    ]

    assert service._is_grounded_relevant_evidence(
        "FILE:app/main.py shows `body = await request.json()`",
        evidence,
    )
    assert not service._is_grounded_relevant_evidence(
        "FILE:app/routes.py implements OAuth login and retries",
        evidence,
    )
    assert not service._is_grounded_relevant_evidence(
        "FILE:app/main.py implements OAuth login and retries",
        evidence,
    )


@pytest.mark.unit
def test_fallback_relevant_evidence_uses_actual_code_snippet():
    service = OpenAILLMService()
    evidence = [
        {
            "type": "repo_context",
            "ref": "FILE:requirements.txt",
            "snippet": "fastapi",
        },
        {
            "type": "code_snippet",
            "ref": "FILE:app/gemini.py",
            "snippet": "response = model.generate_content(prompt)\nreturn response.text",
        },
    ]

    fallback = service._fallback_relevant_evidence(evidence)

    assert fallback.startswith("FILE:app/gemini.py")
    assert "generate_content" in fallback


@pytest.mark.unit
def test_repo_context_is_not_treated_as_code_evidence():
    service = OpenAILLMService()
    evidence = [
        {
            "type": "repo_context",
            "ref": "FILE:requirements.txt",
            "snippet": "fastapi\ngoogle-generativeai",
        }
    ]

    assert service._source_code_evidence(evidence) == []
    assert service._fallback_relevant_evidence(evidence) == "No code evidence found."
