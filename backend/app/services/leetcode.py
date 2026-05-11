from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests


class LeetCodeService:
    GRAPHQL_URL = "https://leetcode.com/graphql"

    def _normalize_username(self, username: str) -> str:
        value = (username or "").strip().strip("@")
        if not value:
            return ""

        if "leetcode.com" in value:
            parsed = urlparse(value if value.startswith(("http://", "https://")) else f"https://{value}")
            parts = [part for part in parsed.path.split("/") if part]
            if parts and parts[0] in {"u", "profile"} and len(parts) > 1:
                return parts[1]
            if parts:
                return parts[-1]

        return value.rstrip("/")

    def _count_for_difficulty(self, rows: list, difficulty: str) -> Dict[str, int]:
        row = next((item for item in rows if item.get("difficulty") == difficulty), {})
        return {
            "count": int(row.get("count") or 0),
            "submissions": int(row.get("submissions") or 0),
        }

    def _extract_submission_rows(self, matched_user: Dict[str, Any]) -> list:
        stats = matched_user.get("submitStatsGlobal") or matched_user.get("submitStats") or {}
        return stats.get("acSubmissionNum") or []

    def fetch_stats(self, username: str) -> Dict[str, Any]:
        """
        Fetch real LeetCode stats for a username.

        Important: this never returns mock numbers. If LeetCode is unavailable
        or the user is not found, callers get an explicit error and should not
        display the stats as verified candidate data.
        """
        normalized = self._normalize_username(username)
        if not normalized:
            return {"username": "", "error": "No username provided"}

        query = """
        query userProfile($username: String!) {
          matchedUser(username: $username) {
            username
            submitStatsGlobal {
              acSubmissionNum {
                difficulty
                count
                submissions
              }
            }
            submitStats {
              acSubmissionNum {
                difficulty
                count
                submissions
              }
            }
            profile {
              ranking
            }
          }
        }
        """

        try:
            response = requests.post(
                self.GRAPHQL_URL,
                json={"query": query, "variables": {"username": normalized}},
                headers={
                    "Content-Type": "application/json",
                    "Referer": f"https://leetcode.com/u/{normalized}/",
                    "User-Agent": "SignalStack/1.0",
                },
                timeout=8,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return {
                "username": normalized,
                "error": "LeetCode stats unavailable",
                "unavailable": True,
            }

        matched_user: Optional[Dict[str, Any]] = payload.get("data", {}).get("matchedUser")
        if not matched_user:
            return {"username": normalized, "error": "LeetCode user not found"}

        rows = self._extract_submission_rows(matched_user)
        total = self._count_for_difficulty(rows, "All")
        easy = self._count_for_difficulty(rows, "Easy")
        medium = self._count_for_difficulty(rows, "Medium")
        hard = self._count_for_difficulty(rows, "Hard")
        acceptance_rate = None
        if total["submissions"] > 0:
            acceptance_rate = round((total["count"] / total["submissions"]) * 100, 1)

        return {
            "username": matched_user.get("username") or normalized,
            "total_solved": total["count"],
            "easy_solved": easy["count"],
            "medium_solved": medium["count"],
            "hard_solved": hard["count"],
            "ranking": matched_user.get("profile", {}).get("ranking") or "N/A",
            "acceptance_rate": acceptance_rate,
            "is_mock": False,
            "source": "leetcode_graphql",
        }
