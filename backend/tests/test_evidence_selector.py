import pytest

from app.pipeline.evidence_selector import extract_snippets, priority_files


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
