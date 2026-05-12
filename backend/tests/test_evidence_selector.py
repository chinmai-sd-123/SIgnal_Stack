import pytest

from app.pipeline.evidence_selector import extract_snippets, priority_files, score_content_relevance
from app.pipeline.signal_extractor import SignalExtractor


class _FakeGithubForEvidence:
    files = [
        "backend/app/models/job_candidate.py",
        "backend/app/services/leetcode.py",
        "backend/app/services/llm.py",
        "backend/app/config/config.py",
        "backend/requirements.txt",
        "README.md",
    ]
    contents = {
        "backend/app/models/job_candidate.py": "class JobCandidate: pass",
        "backend/app/services/leetcode.py": "class LeetCodeService:\n    GRAPHQL_URL = 'https://leetcode.com/graphql'",
        "backend/app/services/llm.py": (
            "from openai import OpenAI\n\n"
            "class OpenAILLMService:\n"
            "    def __init__(self, settings):\n"
            "        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)\n"
            "    def generate(self, prompt):\n"
            "        return self.client.responses.create(model=self.model, input=prompt)\n"
        ),
        "backend/app/config/config.py": "OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')",
        "backend/requirements.txt": "openai>=2.0.0",
        "README.md": "SignalStack",
    }

    def get_recursive_tree(self, repo_url):
        return self.files, "main"

    def get_file_content(self, repo_url, path):
        return self.contents.get(path, "")


@pytest.mark.unit
def test_extract_snippets_keyword_anchor():
    content = """
line 1
line 2
def handler():
    return True
line 5
""".strip()

    result = extract_snippets("app/main.py", content, keywords=["handler"])
    assert "handler" in result["snippet"]
    assert "return True" in result["snippet"]


@pytest.mark.unit
def test_extract_snippets_returns_full_small_code_file():
    content = "\n".join([
        "from fastapi import FastAPI",
        "",
        "app = FastAPI()",
        "",
        "@app.post('/webhook')",
        "async def webhook():",
        "    return {'status': 'accepted'}",
    ])

    result = extract_snippets("app/main.py", content, max_length=2400, keywords=["webhook"])

    assert result["lines"] == "1-7"
    assert result["snippet"] == content


@pytest.mark.unit
def test_task_specific_code_outranks_generic_project_files():
    files = [
        "go.mod",
        "README.md",
        ".github/workflows/deploy.yml",
        "Dockerfile",
        "cmd/server/main.go",
        "internal/feed/fanout.go",
        "internal/repository/feed_repository.go",
    ]

    ranked = priority_files(files, keywords=["feed", "fanout"], max_files=4)

    assert ranked[0].path == "internal/feed/fanout.go"
    assert ranked[0].category == "task_specific"
    assert "internal/repository/feed_repository.go" in [item.path for item in ranked[:3]]


@pytest.mark.unit
def test_multiple_task_keyword_matches_break_priority_ties():
    files = [
        "internal/handlers/login_handler.go",
        "internal/middleware/auth_middleware.go",
        "internal/middleware/rate_limit.go",
        "cmd/server/main.go",
    ]

    ranked = priority_files(files, keywords=["auth", "rate", "limit", "login"], max_files=3)

    assert ranked[0].path in {"internal/middleware/auth_middleware.go", "internal/middleware/rate_limit.go"}
    assert "internal/handlers/login_handler.go" not in [item.path for item in ranked[:2]]


@pytest.mark.unit
def test_small_project_source_files_are_not_dropped():
    files = [
        "README.md",
        "requirements.txt",
        "app/__init__.py",
        "app/main.py",
        "app/gemini.py",
        "app/github.py",
        "app/security.py",
    ]

    ranked = priority_files(files, keywords=["code", "review", "github"], max_files=10)
    paths = [item.path for item in ranked]

    assert "app/main.py" in paths
    assert "app/gemini.py" in paths
    assert "app/github.py" in paths
    assert "app/security.py" in paths
    assert "app/__init__.py" not in paths


@pytest.mark.unit
def test_ai_provider_keywords_prioritize_llm_files_over_generic_models():
    files = [
        "backend/app/models/job_candidate.py",
        "backend/app/models/outcome.py",
        "backend/app/services/leetcode.py",
        "backend/app/services/llm.py",
        "backend/app/config/config.py",
        "backend/seed_eval_candidates.py",
        "backend/requirements.txt",
    ]
    keywords = [
        "openai", "claude", "gemini", "llm", "api_key",
        "credentials", "client",
    ]

    ranked = priority_files(files, keywords=keywords, max_files=5)
    paths = [item.path for item in ranked]

    assert paths[0] == "backend/app/services/llm.py"
    assert "backend/app/models/job_candidate.py" not in paths[:3]
    assert "backend/app/models/outcome.py" not in paths[:3]


@pytest.mark.unit
def test_content_relevance_detects_openai_client_usage():
    content = """
from openai import OpenAI

client = OpenAI(api_key=settings.OPENAI_API_KEY)
response = client.responses.create(model=model, input=prompt)
"""

    score = score_content_relevance(
        "backend/app/services/llm.py",
        content,
        ["openai", "api_key", "client", "responses.create"],
    )

    assert score >= 30


@pytest.mark.unit
def test_task_context_extracts_ai_provider_keywords_from_slash_separated_signal():
    extractor = SignalExtractor()
    task_context = """
Outcome: Productionize AI Backend Services
Outcome Description: Candidate can convert an AI prototype into a backend API.
Signal: Code integrating OpenAI/Claude/Gemini API calls with configurable credentials and client usage
"""

    keywords = {item.lower() for item in extractor._get_evidence_keywords(task_context)}

    assert {"openai", "claude", "gemini", "llm", "api_key"} <= keywords
    assert "candidate" not in keywords
    assert "outcome" not in keywords


@pytest.mark.unit
def test_extract_evidence_promotes_actual_openai_client_file():
    extractor = SignalExtractor()
    extractor.github = _FakeGithubForEvidence()
    task_context = """
Outcome: Productionize AI Backend Services
Outcome Description: Candidate can convert an AI prototype into a working backend service.
Signal: Code integrating OpenAI/Claude/Gemini API calls with configurable credentials and client usage
"""

    evidence = extractor.extract_evidence(
        repo_url="https://github.com/chinmai-sd-123/SIgnal_Stack",
        task_title=task_context,
    )
    code_refs = [item.ref for item in evidence if item.type == "code_snippet"]

    assert code_refs[0] == "FILE:backend/app/services/llm.py"
    assert "OpenAI(api_key=settings.OPENAI_API_KEY)" in evidence[0].snippet
    assert "responses.create" in evidence[0].snippet
