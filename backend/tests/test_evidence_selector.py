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
    assert result["lines"].startswith("2") or result["lines"].startswith("3")


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
