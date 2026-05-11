import pytest

from app.services.repo_selector import matches_any_pattern, MANIFEST_PATTERNS, detect_language_from_file


@pytest.mark.unit
def test_manifest_pattern_matches():
    assert matches_any_pattern("package.json", MANIFEST_PATTERNS)
    assert matches_any_pattern("requirements.txt", MANIFEST_PATTERNS)


@pytest.mark.unit
def test_detect_language_from_manifest():
    assert detect_language_from_file("package.json") == "javascript"
    assert detect_language_from_file("requirements.txt") == "python"
