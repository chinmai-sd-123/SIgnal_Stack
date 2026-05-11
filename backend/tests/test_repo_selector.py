import pytest

from app.services.repo_selector import (
    MANIFEST_PATTERNS,
    RepoSelector,
    detect_language_from_file,
    matches_any_pattern,
    parse_github_repo_url,
)


@pytest.mark.unit
def test_manifest_pattern_matches():
    assert matches_any_pattern("package.json", MANIFEST_PATTERNS)
    assert matches_any_pattern("requirements.txt", MANIFEST_PATTERNS)


@pytest.mark.unit
def test_detect_language_from_manifest():
    assert detect_language_from_file("package.json") == "javascript"
    assert detect_language_from_file("requirements.txt") == "python"


class FakeRepoSelector(RepoSelector):
    def __init__(self, repos, contents):
        super().__init__(github_token=None)
        self.repos = repos
        self.contents = contents

    def _get_user_repos(self, username: str, limit: int = 30):
        return self.repos

    def _get_repo_contents(self, owner: str, repo: str):
        return self.contents.get(repo, [])


def repo_payload(name, language="TypeScript", pushed_at="2026-05-01T00:00:00Z", size=1200, **overrides):
    payload = {
        "full_name": f"candidate/{name}",
        "owner": {"login": "candidate"},
        "name": name,
        "html_url": f"https://github.com/candidate/{name}",
        "language": language,
        "pushed_at": pushed_at,
        "size": size,
        "fork": False,
        "description": "",
    }
    payload.update(overrides)
    return payload


@pytest.mark.unit
def test_manifest_score_prefers_specific_typescript_manifest():
    selector = RepoSelector(github_token=None)

    score, has_manifest, language = selector._manifest_score(["package.json", "tsconfig.json"])

    assert score == 1.0
    assert has_manifest is True
    assert language == "typescript"


@pytest.mark.unit
def test_language_match_handles_common_framework_aliases():
    selector = RepoSelector(github_token=None)

    assert selector._language_match_score("TypeScript", ["Node.js"]) == 0.8
    assert selector._language_match_score("Python", ["FastAPI"]) == 1.0
    assert selector._language_match_score("C#", ["dotnet"]) == 1.0


@pytest.mark.unit
def test_name_match_not_diluted_by_long_job_description():
    selector = RepoSelector(github_token=None)
    keywords = [
        "Backend Engineer",
        "authentication",
        "payments",
        "observability",
        "dashboards",
        "deployments",
        "postgres",
        "queues",
        "caching",
        "webhooks",
    ]

    assert selector._fuzzy_name_match("auth-api", keywords) > selector._fuzzy_name_match("portfolio-site", keywords)


@pytest.mark.unit
def test_select_repos_ranks_job_relevant_repo_above_recent_distractor():
    repos = [
        repo_payload("portfolio-site", pushed_at="2026-05-10T00:00:00Z"),
        repo_payload("auth-api", pushed_at="2026-03-01T00:00:00Z"),
        repo_payload("tutorial-auth-api", pushed_at="2026-05-10T00:00:00Z", description="tutorial project"),
    ]
    selector = FakeRepoSelector(
        repos=repos,
        contents={
            "portfolio-site": ["package.json", "tsconfig.json"],
            "auth-api": ["package.json", "tsconfig.json"],
            "tutorial-auth-api": ["package.json", "tsconfig.json"],
        },
    )
    job = {
        "title": "Backend API Engineer",
        "required_languages": ["Node.js"],
        "description": "Build authentication APIs with secure sessions, database-backed users, and production monitoring.",
    }

    selected = selector.select_repos_for_candidate({"github_username": "candidate"}, job, max_repos=3)

    assert [repo.repo for repo in selected] == ["auth-api", "portfolio-site"]
    assert selected[0].breakdown["name_match"] > selected[1].breakdown["name_match"]


@pytest.mark.unit
def test_github_repo_url_parser_supports_common_formats():
    assert parse_github_repo_url("https://github.com/acme/auth-api") == ("acme", "auth-api")
    assert parse_github_repo_url("git@github.com:acme/auth-api.git") == ("acme", "auth-api")
    assert parse_github_repo_url("acme/auth-api") == ("acme", "auth-api")
