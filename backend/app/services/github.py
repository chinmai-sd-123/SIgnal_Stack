import requests
import base64
from typing import List, Dict
from app.config.config import config

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

    def _normalize_repo_url(self, repo_url: str) -> tuple[str, str]:
        """Extract owner and repo from various GitHub URL formats."""
        # Remove trailing slashes
        url = repo_url.rstrip('/')
        # Remove .git suffix if present (using endswith to avoid stripping other chars)
        if url.endswith('.git'):
            url = url[:-4]
            
        parts = url.split('/')
        owner, repo = parts[-2], parts[-1]
        return owner, repo

    def _request(self, url: str) -> requests.Response:
        """Helper to make requests with retry logic for public repos."""
        session = requests.Session()
        session.trust_env = False  # Fix for local environment proxy issues
        
        try:
            response = session.get(url, headers=self.headers)
            if response.status_code in [401, 403, 404] and self.token:
                # Try without token (in case token is invalid or rate limited but public access works)
                print(f"Request failed with {response.status_code}. Retrying without token...")
                headers = {"User-Agent": "SignalStack-Agent/1.0"}
                response = session.get(url, headers=headers)
            return response
        except Exception as e:
            print(f"Request error: {e}")
            return None

    def get_repo_content(self, repo_url: str, path: str = "") -> List[Dict]:
        # Extract owner/repo from URL
        try:
            owner, repo = self._normalize_repo_url(repo_url)
        except:
            return []

        url = f"{self.api_base}/repos/{owner}/{repo}/contents/{path}"
        response = self._request(url)
        if response and response.status_code == 200:
            return response.json()
        return []

    def get_file_content(self, repo_url: str, file_path: str) -> str:
        try:
            owner, repo = self._normalize_repo_url(repo_url)
            url = f"{self.api_base}/repos/{owner}/{repo}/contents/{file_path}"
            response = self._request(url)
            if response and response.status_code == 200:
                data = response.json()
                # Handle case where path is a directory (returns list) vs file (returns dict)
                if isinstance(data, list):
                    return ""  # It's a directory, not a file
                content = data.get("content", "")
                return base64.b64decode(content).decode('utf-8')
        except Exception as e:
            print(f"Error fetching file {file_path}: {e}")
        return ""

    def get_recursive_tree(self, repo_url: str) -> tuple[List[str], str]:
        # Get default branch sha first
        default_branch = "main"
        try:
            owner, repo = self._normalize_repo_url(repo_url)
            
            # Get repo info to find default branch
            repo_url_api = f"{self.api_base}/repos/{owner}/{repo}"
            repo_response = self._request(repo_url_api)
            
            if repo_response and repo_response.status_code == 200:
                default_branch = repo_response.json().get("default_branch", "main")
            
            tree_url = f"{self.api_base}/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
            response = self._request(tree_url)
            
            if response and response.status_code == 200:
                return [item['path'] for item in response.json().get('tree', [])], default_branch
        except Exception as e:
            print(f"Error getting tree: {e}")
            pass
        return [], default_branch

    def get_commit_history(self, repo_url: str, limit: int = 50) -> List[Dict]:
        try:
            owner, repo = self._normalize_repo_url(repo_url)
            url = f"{self.api_base}/repos/{owner}/{repo}/commits?per_page={limit}"
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                commits = []
                for item in response.json():
                    commit = item.get("commit", {})
                    author = commit.get("author", {})
                    commits.append({
                        "message": commit.get("message", ""),
                        "author_name": author.get("name", "Unknown"),
                        "date": author.get("date", ""),
                        "sha": item.get("sha", "")
                    })
                return commits
        except Exception as e:
            print(f"Error fetching commits: {e}")
        return []
