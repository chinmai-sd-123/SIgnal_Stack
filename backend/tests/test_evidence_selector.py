import pytest

from app.pipeline.evidence_selector import extract_snippets


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
