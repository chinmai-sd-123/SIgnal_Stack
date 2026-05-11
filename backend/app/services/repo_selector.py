"""
Repo Selector Service

Selects the top 3 most relevant repositories for a candidate based on:
1. Fuzzy name matching (project name vs resume projects / outcome keywords)
2. Manifest score (presence of package.json, requirements.txt, etc.)
3. Recency score (recent commits)
4. Size score (not too tiny, not too huge)
5. Language matching (match job requirements)
"""

import logging
import re
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

import requests

from app.config.config import config
from app.services.cache import cache


logger = logging.getLogger(__name__)


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

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "build", "built", "by", "for",
    "from", "in", "into", "is", "of", "on", "or", "role", "that", "the", "this",
    "to", "using", "with", "work", "will", "you", "your",
    "candidate", "developer", "engineer", "intern", "senior", "junior",
}

TOKEN_ALIASES = {
    "authentication": "auth",
    "authenticate": "auth",
    "authorization": "auth",
    "authorize": "auth",
    "authorisation": "auth",
    "authn": "auth",
    "authz": "auth",
    "oauth": "auth",
    "jwt": "auth",
    "postgresql": "postgres",
    "postgres": "postgres",
    "database": "db",
    "databases": "db",
    "frontend": "front",
    "backend": "back",
}

LANGUAGE_ALIASES = {
    "js": "javascript",
    "node": "javascript",
    "nodejs": "javascript",
    "node.js": "javascript",
    "react": "javascript",
    "reactjs": "javascript",
    "react.js": "javascript",
    "next": "javascript",
    "nextjs": "javascript",
    "next.js": "javascript",
    "ts": "typescript",
    "py": "python",
    "django": "python",
    "flask": "python",
    "fastapi": "python",
    "jupyter": "python",
    "jupyter notebook": "python",
    "golang": "go",
    "c sharp": "csharp",
    "c#": "csharp",
    "c-sharp": "csharp",
    "csharp": "csharp",
    ".net": "csharp",
    "dotnet": "csharp",
}

MANIFEST_LANGUAGE_PRIORITY = {
    "typescript": 90,
    "javascript": 80,
    "python": 75,
    "go": 70,
    "rust": 70,
    "java": 65,
    "kotlin": 65,
    "csharp": 65,
}


def _canonical_language(language: Optional[str]) -> Optional[str]:
    if not language:
        return None
    normalized = re.sub(r"\s+", " ", str(language).strip().lower())
    compact = normalized.replace("-", "").replace("_", "").replace(" ", "")
    return LANGUAGE_ALIASES.get(normalized) or LANGUAGE_ALIASES.get(compact) or normalized


def _tokenize_text(value: Any) -> List[str]:
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value or ""))
    tokens = re.findall(r"[a-zA-Z0-9+#.]+", text.lower())
    result = []
    for token in tokens:
        token = TOKEN_ALIASES.get(token, token)
        if token and token not in STOP_WORDS and len(token) > 1:
            result.append(token)
    return result


def parse_github_repo_url(url: str) -> Optional[tuple[str, str]]:
    """Extract (owner, repo) from common GitHub URL formats."""
    cleaned = str(url or "").strip().rstrip("/")
    if not cleaned:
        return None

    cleaned = re.sub(r"\.git$", "", cleaned)
    match = re.search(r"github\.com[:/](?P<owner>[^/\s]+)/(?P<repo>[^/\s?#]+)", cleaned, re.IGNORECASE)
    if not match and re.match(r"^[^/\s]+/[^/\s]+$", cleaned):
        owner, repo = cleaned.split("/", 1)
        return owner, re.sub(r"\.git$", "", repo)
    if not match:
        return None
    return match.group("owner"), re.sub(r"\.git$", "", match.group("repo"))


class RepoSelector:
    """Selects the most relevant repositories for a candidate."""

    def __init__(self, github_token: Optional[str] = None, max_rate_limit_wait: int = 60):
        self.token = github_token or config.GITHUB_TOKEN
        self.headers = {
            "Authorization": f"token {self.token}",
            "User-Agent": "SignalStack-Agent/1.0"
        } if self.token else {
            "User-Agent": "SignalStack-Agent/1.0"
        }
        self.api_base = "https://api.github.com"
        self.max_rate_limit_wait = max_rate_limit_wait
        self._session = requests.Session()
        # Respect environment proxy settings if present.
        self._session.trust_env = True

    def _request(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """Make a GitHub API request with basic retries and rate-limit handling."""
        headers = self.headers.copy()

        for attempt in range(max_retries):
            try:
                response = self._session.get(url, headers=headers, timeout=10)

                remaining = response.headers.get("X-RateLimit-Remaining")
                reset_at = response.headers.get("X-RateLimit-Reset")
                remaining_int = None
                if remaining is not None:
                    try:
                        remaining_int = int(remaining)
                    except ValueError:
                        remaining_int = None

                if response.status_code == 403 and remaining_int == 0 and reset_at:
                    wait = max(0, int(reset_at) - int(time.time())) + 2
                    if wait > self.max_rate_limit_wait:
                        logger.warning("[RepoSelector] Rate limit exhausted for %ss; skipping request.", wait)
                        return None
                    logger.warning("[RepoSelector] Rate limit exhausted. Waiting %ss.", wait)
                    time.sleep(wait)
                    continue

                if response.status_code == 429:
                    try:
                        retry_after = int(response.headers.get("Retry-After", 60))
                    except ValueError:
                        retry_after = 60
                    retry_after = min(retry_after, self.max_rate_limit_wait)
                    logger.warning("[RepoSelector] 429 received. Waiting %ss (attempt %s).", retry_after, attempt + 1)
                    time.sleep(retry_after)
                    continue

                if response.status_code >= 500:
                    wait = (2 ** attempt) * 2
                    logger.warning("[RepoSelector] %s error. Backing off %ss (attempt %s).", response.status_code, wait, attempt + 1)
                    time.sleep(wait)
                    continue

                if response.status_code in (401, 403) and self.token:
                    logger.warning("[RepoSelector] %s with token. Retrying without token.", response.status_code)
                    headers = {"User-Agent": "SignalStack-Agent/1.0"}
                    continue

                if response.status_code == 200:
                    return response

                logger.warning("[RepoSelector] GitHub API error %s for %s", response.status_code, url)
                return None
            except requests.exceptions.RequestException as e:
                logger.warning("[RepoSelector] Request error: %s", e)
                if attempt == max_retries - 1:
                    return None
                time.sleep((2 ** attempt) * 2)
                continue

        logger.warning("[RepoSelector] All %s attempts failed for %s", max_retries, url)
        return None

    def _get_user_repos(self, username: str, limit: int = 30) -> List[Dict]:
        """Fetch user's public repositories."""
        url = f"{self.api_base}/users/{username}/repos?per_page={limit}&sort=updated"
        cached = cache.get_github_response(url)
        if isinstance(cached, list):
            return cached
        response = self._request(url)
        if response:
            data = response.json()
            cache.set_github_response(url, data)
            return data
        return []

    def _get_repo_info(self, owner: str, repo: str) -> Optional[Dict]:
        """Get detailed info for a single repo."""
        url = f"{self.api_base}/repos/{owner}/{repo}"
        cached = cache.get_github_response(url)
        if isinstance(cached, dict):
            return cached
        response = self._request(url)
        if response:
            data = response.json()
            cache.set_github_response(url, data)
            return data
        return None

    def _get_repo_contents(self, owner: str, repo: str) -> List[str]:
        """Get root-level file names."""
        url = f"{self.api_base}/repos/{owner}/{repo}/contents"
        cached = cache.get_github_response(url)
        if isinstance(cached, list):
            return [item.get("name", "") for item in cached if isinstance(item, dict)]
        response = self._request(url)
        if response:
            data = response.json()
            cache.set_github_response(url, data)
            return [item.get("name", "") for item in data if isinstance(item, dict)]
        return []

    def _fuzzy_name_match(self, repo_name: str, keywords: List[str]) -> float:
        """
        Calculate fuzzy match score between repo name and keywords.
        Returns 0.0 to 1.0
        """
        if not keywords:
            return 0.0

        repo_tokens = set(_tokenize_text(repo_name))
        if not repo_tokens:
            return 0.0

        phrase_scores = []
        keyword_tokens = set()
        for kw in keywords:
            phrase_tokens = set(_tokenize_text(kw))
            if not phrase_tokens:
                continue
            keyword_tokens.update(phrase_tokens)
            overlap = repo_tokens & phrase_tokens
            if not overlap:
                continue
            coverage = len(overlap) / len(phrase_tokens)
            density = len(overlap) / len(repo_tokens)
            phrase_scores.append((coverage * 0.75) + (density * 0.25))

        if not keyword_tokens or not phrase_scores:
            return 0.0

        intersection = repo_tokens & keyword_tokens
        aggregate = len(intersection) / max(len(repo_tokens), 1)
        score = max(max(phrase_scores), aggregate * 0.8)
        return max(0.0, min(1.0, score))

    def _manifest_score(self, root_files: List[str]) -> tuple[float, bool, Optional[str]]:
        """
        Check for manifest files using fuzzy pattern matching.
        Returns (score, has_manifest, detected_language).
        """
        detected_languages = []
        for fname in root_files:
            detected_language = detect_language_from_file(fname)
            if detected_language:
                detected_languages.append(detected_language)
        if detected_languages:
            detected_language = max(
                detected_languages,
                key=lambda lang: MANIFEST_LANGUAGE_PRIORITY.get(lang, 0),
            )
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
        POPULAR_LANGUAGES = ["python", "javascript", "typescript", "java", "go", "rust", "c++", "csharp"]
        repo_lang = _canonical_language(repo_language)
        
        if not required_languages:
            # No requirements: score based on language popularity
            if repo_lang and repo_lang in POPULAR_LANGUAGES:
                return 0.7  # Boost for popular languages
            return 0.5  # Neutral

        if not repo_lang:
            return 0.3  # Unknown language

        required = [_canonical_language(lang) for lang in required_languages]
        required = [lang for lang in required if lang]

        if repo_lang in required:
            return 1.0
        # Partial match for related languages
        related = {
            "javascript": ["typescript", "javascript", "js", "ts"],
            "typescript": ["javascript", "typescript", "js", "ts"],
            "python": ["python", "jupyter notebook"],
            "java": ["kotlin", "scala"],
            "csharp": ["f#", "vb.net"],
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
            parsed = parse_github_repo_url(candidate["repo_url"])
            if parsed:
                owner, repo_name = parsed
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
            if job.get("description"):
                # Extract meaningful words from description
                desc_words = _tokenize_text(job["description"])
                keywords.extend(desc_words[:10])
        if candidate.get("resume_projects"):
            keywords.extend(candidate["resume_projects"])

        required_languages = job.get("required_languages", []) if job else []

        # 4. Score each repo
        scored_repos: List[tuple[tuple, RepoScore]] = []
        seen_repos = set()

        for repo_data in repos_to_score:
            owner = repo_data.get("owner", {}).get("login", "")
            repo_name = repo_data.get("name", "")
            repo_key = (repo_data.get("full_name") or f"{owner}/{repo_name}").lower()
            if repo_key in seen_repos:
                continue
            seen_repos.add(repo_key)

            # Skip forks/tutorials
            if self._is_fork_or_tutorial(repo_data):
                continue

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

            score = RepoScore(
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
            )
            ideal_size_distance = abs(size_kb - 1000)
            sort_key = (
                -total_score,
                -lang_match,
                -manifest_val,
                -name_score,
                -recency,
                ideal_size_distance,
                repo_name.lower(),
            )
            scored_repos.append((sort_key, score))

        # 5. Sort by score descending and return top N
        scored_repos.sort(key=lambda item: item[0])
        return [repo_score for _, repo_score in scored_repos[:max_repos]]


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
