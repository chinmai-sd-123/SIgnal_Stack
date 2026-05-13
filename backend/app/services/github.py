import base64
import logging
import time
from typing import List, Dict, Tuple, Optional

import requests

from app.config.config import config
from app.services.cache import cache


logger = logging.getLogger(__name__)


class GitHubService:
    def __init__(self):
        self.token = config.GITHUB_TOKEN
        self.headers = {
            "Authorization": f"token {self.token}",
            "User-Agent": "SignalStack-Agent/1.0"
        } if self.token else {
            "User-Agent": "SignalStack-Agent/1.0"
        }
        self.api_base = "https://api.github.com"
        self._session = requests.Session()
        self._session.trust_env = False

    def _normalize_repo_url(self, repo_url: str) -> Tuple[str, str]:
        """Extract owner and repo from various GitHub URL formats."""
        url = repo_url.rstrip('/')
        if url.endswith('.git'):
            url = url[:-4]
        parts = url.split('/')
        if len(parts) < 2:
            raise ValueError("Invalid GitHub URL")
        owner, repo = parts[-2], parts[-1]
        return owner, repo

    def _backoff_seconds(self, attempt: int) -> int:
        return min((2 ** attempt) * 2, 10)

    def _sleep_before_retry(self, seconds: int, attempt: int, max_retries: int, reason: str):
        if attempt >= max_retries - 1:
            return
        logger.warning(
            "[GitHub] %s. Backing off %ss (attempt %s/%s).",
            reason,
            seconds,
            attempt + 1,
            max_retries,
        )
        time.sleep(seconds)

    def _request(self, url: str, max_retries: int = 4) -> Optional[requests.Response]:
        """
        Make a GET request with:
        - Exponential backoff on 429 / 500-range errors
        - Retry-After header respect
        - RateLimit-Remaining awareness (pause before hitting zero)
        - Unauthenticated fallback on 401/403 (for public repos)
        """
        headers = self.headers.copy()

        last_error = None
        for attempt in range(max_retries):
            try:
                response = self._session.get(url, headers=headers, timeout=15)

                remaining = response.headers.get("X-RateLimit-Remaining")
                reset_at = response.headers.get("X-RateLimit-Reset")
                remaining_int = None
                if remaining is not None:
                    try:
                        remaining_int = int(remaining)
                    except ValueError:
                        remaining_int = None

                # ── Rate limit: pause if we're nearly out of calls ──────────
                if remaining_int is not None and remaining_int < 5 and reset_at:
                    wait = max(0, int(reset_at) - int(time.time())) + 2
                    logger.warning("[GitHub] Rate limit nearly exhausted. Waiting %ss.", wait)
                    time.sleep(wait)

                # ── 403 with rate limit exhausted ──────────────────────────
                if response.status_code == 403 and remaining_int == 0 and reset_at:
                    wait = max(0, int(reset_at) - int(time.time())) + 2
                    logger.warning("[GitHub] Rate limit exhausted. Waiting %ss.", wait)
                    time.sleep(wait)
                    continue

                # ── 429 Too Many Requests: respect Retry-After ───────────────
                if response.status_code == 429:
                    try:
                        retry_after = int(response.headers.get("Retry-After", 60))
                    except (TypeError, ValueError):
                        retry_after = self._backoff_seconds(attempt)
                    self._sleep_before_retry(retry_after, attempt, max_retries, "429 received")
                    continue

                # ── 5xx server errors: exponential backoff ───────────────────
                if response.status_code >= 500:
                    self._sleep_before_retry(
                        self._backoff_seconds(attempt),
                        attempt,
                        max_retries,
                        f"{response.status_code} error",
                    )
                    continue

                # ── Auth failure on token: retry without token (public repos) ─
                if response.status_code in (401, 403) and self.token:
                    logger.warning("[GitHub] %s with token. Retrying without token.", response.status_code)
                    headers = {"User-Agent": "SignalStack-Agent/1.0"}
                    continue

                return response

            except requests.exceptions.Timeout as e:
                last_error = e
                self._sleep_before_retry(
                    self._backoff_seconds(attempt),
                    attempt,
                    max_retries,
                    "timeout",
                )
            except requests.exceptions.RequestException as e:
                last_error = e
                self._sleep_before_retry(
                    self._backoff_seconds(attempt),
                    attempt,
                    max_retries,
                    f"request error: {e}",
                )

        logger.warning("[GitHub] All %s attempts failed for %s. Last error: %s", max_retries, url, last_error)
        return None

    def get_repo_content(self, repo_url: str, path: str = "") -> List[Dict]:
        try:
            owner, repo = self._normalize_repo_url(repo_url)
        except Exception:
            return []
        url = f"{self.api_base}/repos/{owner}/{repo}/contents/{path}"
        cached = cache.get_github_response(url)
        if cached is not None:
            return cached
        response = self._request(url)
        if response and response.status_code == 200:
            data = response.json()
            cache.set_github_response(url, data)
            return data
        return []

    def get_repo_metadata(self, repo_url: str) -> Dict:
        """
        Fetch repo-level metadata: fork status, parent repo, star count,
        default branch, size, open issues.
        """
        try:
            owner, repo = self._normalize_repo_url(repo_url)
            url = f"{self.api_base}/repos/{owner}/{repo}"
            cached = cache.get_github_response(url)
            if isinstance(cached, dict):
                return cached
            response = self._request(url)
            if response and response.status_code == 200:
                data = response.json()
                parent = data.get("parent") or {}
                result = {
                    "is_fork": data.get("fork", False),
                    "parent_full_name": parent.get("full_name", ""),
                    "parent_url": parent.get("html_url", ""),
                    "stargazers_count": data.get("stargazers_count", 0),
                    "forks_count": data.get("forks_count", 0),
                    "size_kb": data.get("size", 0),
                    "open_issues_count": data.get("open_issues_count", 0),
                    "default_branch": data.get("default_branch", "main"),
                    "created_at": data.get("created_at", ""),
                    "pushed_at": data.get("pushed_at", ""),
                    "description": data.get("description", ""),
                }
                cache.set_github_response(url, result)
                return result
        except Exception as e:
            logger.warning("[GitHub] Error fetching repo metadata: %s", e)
        return {"is_fork": False}

    def get_file_content(self, repo_url: str, file_path: str) -> str:
        try:
            owner, repo = self._normalize_repo_url(repo_url)
            url = f"{self.api_base}/repos/{owner}/{repo}/contents/{file_path}"
            cached = cache.get_github_response(url)
            if isinstance(cached, str):
                return cached
            if isinstance(cached, dict) and cached.get("content"):
                content = cached.get("content", "")
                encoding = cached.get("encoding")
                if encoding == "base64":
                    return base64.b64decode(content).decode("utf-8", errors="replace")
                return content
            response = self._request(url)
            if response and response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    return ""  # path is a directory
                content = data.get("content", "")
                if content:
                    cache.set_github_response(url, data)
                    return base64.b64decode(content).decode("utf-8", errors="replace")
                download_url = data.get("download_url")
                if download_url:
                    raw = self._request(download_url)
                    if raw and raw.status_code == 200:
                        text = raw.text
                        cache.set_github_response(url, text)
                        return text
        except Exception as e:
            logger.warning("[GitHub] Error fetching file %s: %s", file_path, e)
        return ""

    def get_recursive_tree(self, repo_url: str) -> Tuple[List[str], str]:
        """
        Get all file paths in the repo.

        Strategy:
        1. Try the recursive Git tree API (one call, fast).
        2. If truncated=true, fall back to directory-walking via the
           Contents API (handles repos with >100k blobs).
        """
        default_branch = "main"
        try:
            owner, repo = self._normalize_repo_url(repo_url)

            # ── Step 1: Get default branch ───────────────────────────────────
            meta_response = self._request(f"{self.api_base}/repos/{owner}/{repo}")
            if meta_response and meta_response.status_code == 200:
                default_branch = meta_response.json().get("default_branch", "main")

            # ── Step 2: Recursive tree (fast path) ───────────────────────────
            tree_url = f"{self.api_base}/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
            cached = cache.get_github_response(tree_url)
            if isinstance(cached, dict) and cached.get("paths"):
                return cached.get("paths", []), cached.get("default_branch", default_branch)
            response = self._request(tree_url)

            if response and response.status_code == 200:
                data = response.json()
                truncated = data.get("truncated", False)
                paths = [
                    item["path"]
                    for item in data.get("tree", [])
                    if item.get("type") == "blob"  # blobs only, skip tree entries
                ]

                if not truncated:
                    cache.set_github_response(tree_url, {"paths": paths, "default_branch": default_branch})
                    return paths, default_branch

                # ── Step 3: Fallback — walk directories via Contents API ───────
                logger.warning("[GitHub] Tree truncated for %s/%s. Falling back to directory walk.", owner, repo)
                walked = self._walk_contents(owner, repo, "", default_branch)
                # Merge: keep recursive-tree paths + fill in what was cut off
                all_paths = list(dict.fromkeys(paths + walked))  # preserve order, deduplicate
                cache.set_github_response(tree_url, {"paths": all_paths, "default_branch": default_branch})
                return all_paths, default_branch

        except Exception as e:
            logger.warning("[GitHub] Error getting tree: %s", e)

        return [], default_branch

    def _walk_contents(
        self,
        owner: str,
        repo: str,
        path: str,
        branch: str,
        depth: int = 0,
        max_depth: int = 6,
        max_files: int = 2000,
        _collected: List[str] = None
    ) -> List[str]:
        """
        Recursively walk the Contents API to enumerate files.
        Used only when the Git tree is truncated.

        Caps at max_files to avoid runaway API calls on monorepos.
        """
        if _collected is None:
            _collected = []
        if depth > max_depth or len(_collected) >= max_files:
            return _collected

        url = f"{self.api_base}/repos/{owner}/{repo}/contents/{path}"
        if branch:
            url += f"?ref={branch}"

        response = self._request(url)
        if not response or response.status_code != 200:
            return _collected

        items = response.json()
        if not isinstance(items, list):
            return _collected

        for item in items:
            if len(_collected) >= max_files:
                break
            item_type = item.get("type")
            item_path = item.get("path", "")
            if item_type == "file":
                _collected.append(item_path)
            elif item_type == "dir":
                # Skip known noise directories entirely
                dirname = item_path.split("/")[-1].lower()
                if dirname in {"node_modules", ".git", "venv", "__pycache__", "dist", "build", "vendor"}:
                    continue
                self._walk_contents(owner, repo, item_path, branch, depth + 1, max_depth, max_files, _collected)

        return _collected

    def get_commit_history(self, repo_url: str, limit: int = 50) -> List[Dict]:
        try:
            owner, repo = self._normalize_repo_url(repo_url)
            url = f"{self.api_base}/repos/{owner}/{repo}/commits?per_page={limit}"
            cached = cache.get_github_response(url)
            if isinstance(cached, list):
                return cached
            response = self._request(url)
            if response and response.status_code == 200:
                commits = []
                for item in response.json():
                    commit = item.get("commit", {})
                    git_author = commit.get("author", {})
                    github_user = item.get("author") or {}
                    commits.append({
                        "message": commit.get("message", ""),
                        "author_name": git_author.get("name", "Unknown"),
                        "author_email": git_author.get("email", "").lower().strip(),
                        "github_login": github_user.get("login", ""),
                        "date": git_author.get("date", ""),
                        "sha": item.get("sha", "")
                    })
                cache.set_github_response(url, commits)
                return commits
        except Exception as e:
            logger.warning("[GitHub] Error fetching commits: %s", e)
        return []
