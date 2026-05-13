from app.services.crud import _compact_evidence_items


def test_evidence_compaction_preserves_audit_sections():
    items = [
        {"type": "code_snippet", "ref": "FILE:a.py", "snippet": "a" * 1500, "source_url": "https://github.com/x/y/blob/main/a.py"},
        {"type": "code_snippet", "ref": "FILE:b.py", "snippet": "b", "source_url": "https://github.com/x/y/blob/main/b.py"},
        {"type": "code_snippet", "ref": "FILE:c.py", "snippet": "c", "source_url": "https://github.com/x/y/blob/main/c.py"},
        {"type": "repo_context", "ref": "REPOSITORY", "snippet": "Repository Structure (3 files total):\na.py\nb.py\nc.py"},
        {"type": "authorship_context", "ref": "AUTH:task", "snippet": "AUTHORSHIP CONFIRMED"},
        {"type": "project_health", "ref": "PROJECT_SCAN", "snippet": "Tests Present: YES"},
        {"type": "ai_analysis", "ref": "AI_FINDING:task", "snippet": "Key Evidence (AI Analysis): grounded"},
    ]

    compacted = _compact_evidence_items(items)
    refs = [item["ref"] for item in compacted]

    assert refs == [
        "AI_FINDING:task",
        "FILE:a.py",
        "FILE:b.py",
        "REPOSITORY",
        "AUTH:task",
        "PROJECT_SCAN",
    ]
    assert "FILE:c.py" not in refs
    assert "Open the GitHub source link" in compacted[1]["snippet"]
