"""
Repo Selector Service

Selects the top 3 most relevant repositories for a candidate based on:
1. Fuzzy name matching (project name vs resume projects / outcome keywords)
2. Manifest score (presence of package.json, requirements.txt, etc.)
3. Recency score (recent commits)
4. Size score (not too tiny, not too huge)
5. Language matching (match job requirements)
"""

import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import requests
from app.config.config import config


@dataclass
class RepoScore:
    """Represents a scored repository for candidate evaluation."""
    owner: str
    repo: str
    url: str
    score: float
    manifest_present: bool
    language: Optional[str]
    last_commit_date: Optional[str]
    size_kb: int
    breakdown: Dict[str, float]


# =================== FUZZY FILE PATTERN MATCHING ===================
# Handles variations like: docker.yaml, Docker-compose.yml, config.js, etc.

# Manifest file patterns (regex-based for flexibility)
MANIFEST_PATTERNS = [
    # Python
    (r"^requirements.*\.txt$", "python"),
    (r"^pyproject\.toml$", "python"),
    (r"^setup\.(py|cfg)$", "python"),
    (r"^Pipfile(\.lock)?$", "python"),
    (r"^poetry\.lock$", "python"),
    (r"^environment\.ya?ml$", "python"),  # conda
    # JavaScript/Node
    (r"^package\.json$", "javascript"),
    (r"^(yarn|pnpm-lock|package-lock)\.(yaml|json|lock)$", "javascript"),
    (r"^bun\.lockb$", "javascript"),
    # TypeScript
    (r"^tsconfig.*\.json$", "typescript"),
    # Go
    (r"^go\.(mod|sum)$", "go"),
    # Java
    (r"^pom\.xml$", "java"),
    (r"^build\.gradle(\.kts)?$", "java"),
    (r"^settings\.gradle(\.kts)?$", "java"),
    # Rust
    (r"^Cargo\.(toml|lock)$", "rust"),
    # Ruby
    (r"^Gemfile(\.lock)?$", "ruby"),
    # PHP
    (r"^composer\.(json|lock)$", "php"),
    # .NET
    (r".*\.(csproj|fsproj|vbproj|sln)$", "csharp"),
    (r"^nuget\.config$", "csharp"),
    # Swift/iOS
    (r"^Package\.swift$", "swift"),
    (r"^Podfile(\.lock)?$", "swift"),
    # Kotlin
    (r"^build\.gradle\.kts$", "kotlin"),
]

# Docker/Deployment patterns (flexible naming)
DEPLOYMENT_PATTERNS = [
    r"^[Dd]ocker[-_]?[Cc]ompose.*\.(ya?ml|yml)$",  # docker-compose.yml, Docker-Compose.yaml
    r"^[Dd]ockerfile.*$",  # Dockerfile, Dockerfile.dev, dockerfile.prod
    r"^[Cc]ontainer[-_]?file$",  # Containerfile (Podman)
    r"^Procfile$",  # Heroku
    r"^\.?docker[-_]?ignore$",
    r"^kubernetes.*\.(ya?ml|yml)$",
    r"^k8s.*\.(ya?ml|yml)$",
    r"^helm.*\.(ya?ml|yml)$",
    r"^deploy.*\.(ya?ml|yml|sh)$",
    r"^terraform.*\.(tf|hcl)$",
    r"^pulumi.*\.(yaml|ts|py|go)$",
    r"^serverless\.(ya?ml|yml)$",
    r"^app\.(ya?ml|yml)$",  # Various PaaS configs
    r"^fly\.toml$",  # Fly.io
    r"^render\.ya?ml$",  # Render
    r"^railway\.json$",  # Railway
    r"^vercel\.json$",  # Vercel
    r"^netlify\.toml$",  # Netlify
]

# CI/CD patterns
CI_CD_PATTERNS = [
    r"^\.github/workflows/.*\.(ya?ml|yml)$",  # GitHub Actions
    r"^\.gitlab-ci\.(ya?ml|yml)$",  # GitLab CI
    r"^bitbucket-pipelines\.(ya?ml|yml)$",  # Bitbucket
    r"^\.circleci/.*\.(ya?ml|yml)$",  # CircleCI
    r"^Jenkinsfile.*$",  # Jenkins
    r"^\.travis\.(ya?ml|yml)$",  # Travis CI
    r"^azure-pipelines\.(ya?ml|yml)$",  # Azure DevOps
    r"^\.drone\.(ya?ml|yml)$",  # Drone CI
    r"^cloudbuild\.(ya?ml|yml)$",  # Google Cloud Build
    r"^buildspec\.(ya?ml|yml)$",  # AWS CodeBuild
    r"^appveyor\.(ya?ml|yml)$",  # AppVeyor
]

# Test directory/file patterns
TEST_PATTERNS = [
    r"^tests?/",  # test/ or tests/
    r"^__tests__/",  # Jest convention
    r"^spec/",  # RSpec, Jasmine
    r"^specs?/",
    r".*[_-]?test[_-]?.*\.(py|js|ts|java|go|rs|rb)$",  # *_test.py, test_*.py
    r".*[_-]?spec[_-]?.*\.(py|js|ts|java|go|rs|rb)$",  # *_spec.rb
    r"^pytest\.ini$",
    r"^jest\.config\.(js|ts|json)$",
    r"^\.mocharc\.(js|json|ya?ml)$",
    r"^karma\.conf\.js$",
    r"^phpunit\.xml$",
    r"^tox\.ini$",
    r"^conftest\.py$",
]

# Config file patterns (generic)
CONFIG_PATTERNS = [
    r"^config.*\.(ya?ml|yml|json|toml|ini|cfg|py|js|ts)$",
    r"^settings.*\.(ya?ml|yml|json|toml|ini|cfg|py)$",
    r"^\.env.*$",  # .env, .env.local, .env.production
    r"^env.*\.(ya?ml|yml)$",
    r"^application.*\.(ya?ml|yml|properties)$",  # Spring Boot
    r"^appsettings.*\.json$",  # .NET
]

# ML/AI patterns
ML_MODEL_PATTERNS = [
    r".*\.(pkl|pickle|joblib)$",  # Scikit-learn
    r".*\.(h5|hdf5|keras)$",  # Keras/TensorFlow
    r".*\.(pt|pth|onnx)$",  # PyTorch
    r".*\.safetensors$",  # HuggingFace
    r"^models?/",  # models/ directory
    r"^checkpoints?/",
    r"^weights?/",
]

# Frontend patterns
FRONTEND_PATTERNS = [
    r"^src/.*\.(jsx|tsx|vue|svelte)$",
    r"^components?/",
    r"^pages?/",
    r"^views?/",
    r"^templates?/",
    r".*\.(html|htm)$",
    r"^public/",
    r"^static/",
    r"^assets?/",
]

# Database/Migration patterns
MIGRATION_PATTERNS = [
    r"^migrations?/",
    r"^db/",
    r"^database/",
    r"^alembic/",
    r"^prisma/",
    r"^drizzle/",
    r".*\.sql$",
    r"^schema\.(prisma|graphql)$",
]


def matches_any_pattern(filename: str, patterns: list) -> bool:
    """
    Check if filename matches any of the regex patterns.
    Uses re.search to match patterns anywhere in the path (not just from start).
    """
    for pattern in patterns:
        if isinstance(pattern, tuple):
            pattern = pattern[0]  # Extract regex from (regex, language) tuple
        # Use re.search to match anywhere in the string (handles full paths like tests/test_main.py)
        if re.search(pattern, filename, re.IGNORECASE):
            return True
    return False


def detect_language_from_file(filename: str) -> str:
    """Detect programming language from manifest file."""
    for pattern, language in MANIFEST_PATTERNS:
        if re.match(pattern, filename, re.IGNORECASE):
            return language
    return None

# Deprioritize fork indicators
FORK_INDICATORS = ["forked from", "fork", "tutorial", "example", "demo", "learn", "course"]


class RepoSelector:
    """Selects the most relevant repositories for a candidate."""

    def __init__(self, github_token: Optional[str] = None):
        self.token = github_token or config.GITHUB_TOKEN
        self.headers = {
            "Authorization": f"token {self.token}",
            "User-Agent": "SignalStack-Agent/1.0"
        } if self.token else {
            "User-Agent": "SignalStack-Agent/1.0"
        }
        self.api_base = "https://api.github.com"

    def _request(self, url: str) -> Optional[requests.Response]:
        """Make a GitHub API request with error handling."""
        try:
            session = requests.Session()
            # Respect environment proxy settings if present.
            session.trust_env = True
            response = session.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                return response
            print(f"GitHub API error: {response.status_code} for {url}")
            try:
                print(f"GitHub API response: {response.text[:500]}")
            except Exception:
                pass
        except Exception as e:
            print(f"Request error: {e}")
        return None

    def _get_user_repos(self, username: str, limit: int = 30) -> List[Dict]:
        """Fetch user's public repositories."""
        url = f"{self.api_base}/users/{username}/repos?per_page={limit}&sort=updated"
        response = self._request(url)
        if response:
            return response.json()
        return []

    def _get_repo_info(self, owner: str, repo: str) -> Optional[Dict]:
        """Get detailed info for a single repo."""
        url = f"{self.api_base}/repos/{owner}/{repo}"
        response = self._request(url)
        if response:
            return response.json()
        return None

    def _get_repo_contents(self, owner: str, repo: str) -> List[str]:
        """Get root-level file names."""
        url = f"{self.api_base}/repos/{owner}/{repo}/contents"
        response = self._request(url)
        if response:
            return [item.get("name", "") for item in response.json() if isinstance(item, dict)]
        return []

    def _fuzzy_name_match(self, repo_name: str, keywords: List[str]) -> float:
        """
        Calculate fuzzy match score between repo name and keywords.
        Returns 0.0 to 1.0
        """
        if not keywords:
            return 0.0

        repo_tokens = set(re.split(r'[-_\s]', repo_name.lower()))
        keyword_tokens = set()
        for kw in keywords:
            keyword_tokens.update(re.split(r'[-_\s]', kw.lower()))

        if not keyword_tokens:
            return 0.0

        intersection = repo_tokens & keyword_tokens
        return len(intersection) / max(len(keyword_tokens), 1)

    def _manifest_score(self, root_files: List[str]) -> tuple[float, bool, Optional[str]]:
        """
        Check for manifest files using fuzzy pattern matching.
        Returns (score, has_manifest, detected_language).
        """
        detected_language = None
        for fname in root_files:
            # Use pattern-based matching
            if matches_any_pattern(fname, MANIFEST_PATTERNS):
                detected_language = detect_language_from_file(fname)
                return (1.0, True, detected_language)
        return (0.0, False, None)

    def _recency_score(self, pushed_at: Optional[str]) -> float:
        """
        Score based on how recently the repo was updated.
        More recent = higher score.
        """
        if not pushed_at:
            return 0.0
        try:
            pushed_date = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
            days_ago = (datetime.now(pushed_date.tzinfo) - pushed_date).days
            # Exponential decay: score = exp(-days/180)
            import math
            return max(0.0, min(1.0, math.exp(-days_ago / 180)))
        except:
            return 0.0

    def _size_score(self, size_kb: int) -> float:
        """
        Score based on repo size. Prefer medium-sized repos.
        Too small (< 10KB) = might be trivial
        Too large (> 500MB) = might be a data dump
        """
        if size_kb < 10:
            return 0.2
        elif size_kb < 100:
            return 0.5
        elif size_kb < 10000:  # 10MB
            return 1.0
        elif size_kb < 100000:  # 100MB
            return 0.7
        else:
            return 0.3

    def _is_fork_or_tutorial(self, repo_data: Dict) -> bool:
        """Check if repo is a fork or tutorial/demo."""
        if repo_data.get("fork", False):
            return True
        name = repo_data.get("name", "").lower()
        desc = (repo_data.get("description") or "").lower()
        for indicator in FORK_INDICATORS:
            if indicator in name or indicator in desc:
                return True
        return False

    def _language_match_score(self, repo_language: Optional[str], required_languages: List[str]) -> float:
        """
        Score based on language match with job requirements.
        """
        # Popular languages get a boost when no specific requirements
        POPULAR_LANGUAGES = ["python", "javascript", "typescript", "java", "go", "rust", "c++", "c#"]
        
        if not required_languages:
            # No requirements: score based on language popularity
            if repo_language and repo_language.lower() in POPULAR_LANGUAGES:
                return 0.7  # Boost for popular languages
            return 0.5  # Neutral

        if not repo_language:
            return 0.3  # Unknown language

        repo_lang = repo_language.lower()
        required = [lang.lower() for lang in required_languages]

        if repo_lang in required:
            return 1.0
        # Partial match for related languages
        related = {
            "javascript": ["typescript", "javascript", "js", "ts"],
            "typescript": ["javascript", "typescript", "js", "ts"],
            "python": ["python", "jupyter notebook"],
            "java": ["kotlin", "scala"],
            "c#": ["f#", "vb.net"],
        }
        for lang in required:
            if lang in related and repo_lang in related.get(lang, []):
                return 0.8
        return 0.2  # No match

    def select_repos_for_candidate(
        self,
        candidate: Dict[str, Any],
        job: Optional[Dict[str, Any]] = None,
        max_repos: int = 5
    ) -> List[RepoScore]:
        """
        Select the top N most relevant repos for a candidate.

        Args:
            candidate: Dict with 'github_username' and optionally 'repo_url', 'resume_projects'
            job: Optional Dict with 'title', 'required_languages', 'description'
            max_repos: Maximum number of repos to return (default 3)

        Returns:
            List of RepoScore objects, ordered by score descending
        """
        repos_to_score: List[Dict] = []

        # 1. If candidate provided a specific repo URL, include it
        if candidate.get("repo_url"):
            url = candidate["repo_url"]
            parts = url.rstrip("/").replace(".git", "").split("/")
            if len(parts) >= 2:
                owner, repo_name = parts[-2], parts[-1]
                repo_info = self._get_repo_info(owner, repo_name)
                if repo_info:
                    repos_to_score.append(repo_info)

        # 2. If candidate has GitHub username, fetch their repos
        username = candidate.get("github_username")
        if username:
            user_repos = self._get_user_repos(username)
            repos_to_score.extend(user_repos)

        # 3. Build keyword list from job and candidate info
        keywords = []
        if job:
            keywords.append(job.get("title", ""))
            keywords.extend(job.get("required_languages", []))
            if job.get("description"):
                # Extract meaningful words from description
                desc_words = re.findall(r'\b[a-zA-Z]{4,}\b', job["description"])
                keywords.extend(desc_words[:10])
        if candidate.get("resume_projects"):
            keywords.extend(candidate["resume_projects"])

        required_languages = job.get("required_languages", []) if job else []

        # 4. Score each repo
        scored_repos: List[RepoScore] = []
        seen_repos = set()

        for repo_data in repos_to_score:
            full_name = repo_data.get("full_name", "")
            if full_name in seen_repos:
                continue
            seen_repos.add(full_name)

            # Skip forks/tutorials
            if self._is_fork_or_tutorial(repo_data):
                continue

            owner = repo_data.get("owner", {}).get("login", "")
            repo_name = repo_data.get("name", "")
            repo_url = repo_data.get("html_url", "")
            size_kb = repo_data.get("size", 0)
            pushed_at = repo_data.get("pushed_at")
            repo_language = repo_data.get("language")

            # Get root files for manifest detection
            root_files = self._get_repo_contents(owner, repo_name)
            manifest_val, has_manifest, detected_lang = self._manifest_score(root_files)

            # Use detected language if GitHub's language field is not set
            final_language = repo_language or detected_lang

            # Calculate component scores
            name_score = self._fuzzy_name_match(repo_name, keywords)
            recency = self._recency_score(pushed_at)
            size_scr = self._size_score(size_kb)
            lang_match = self._language_match_score(final_language, required_languages)

            # Weighted total score
            # When no job is provided, boost manifest and recency (more objective signals)
            if job:
                # With job context: name and language match are more important
                # Weights: name=0.25, manifest=0.2, recency=0.2, size=0.1, language=0.25
                total_score = (
                    name_score * 0.25 +
                    manifest_val * 0.20 +
                    recency * 0.20 +
                    size_scr * 0.10 +
                    lang_match * 0.25
                )
            else:
                # Without job context: rely more on objective signals
                # Weights: manifest=0.30, recency=0.30, size=0.15, language=0.25, name=0.0
                total_score = (
                    manifest_val * 0.30 +
                    recency * 0.30 +
                    size_scr * 0.15 +
                    lang_match * 0.25
                )

            scored_repos.append(RepoScore(
                owner=owner,
                repo=repo_name,
                url=repo_url,
                score=round(total_score, 3),
                manifest_present=has_manifest,
                language=final_language,
                last_commit_date=pushed_at,
                size_kb=size_kb,
                breakdown={
                    "name_match": round(name_score, 3),
                    "manifest": round(manifest_val, 3),
                    "recency": round(recency, 3),
                    "size": round(size_scr, 3),
                    "language_match": round(lang_match, 3),
                }
            ))

        # 5. Sort by score descending and return top N
        scored_repos.sort(key=lambda r: r.score, reverse=True)
        return scored_repos[:max_repos]


def select_repos_for_candidate(
    candidate: Dict[str, Any],
    job: Optional[Dict[str, Any]] = None,
    max_repos: int = 3
) -> List[RepoScore]:
    """
    Convenience function to select repos without instantiating the class.
    """
    selector = RepoSelector()
    return selector.select_repos_for_candidate(candidate, job, max_repos)
