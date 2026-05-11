import requests
from typing import Dict, Any, Optional

class LeetCodeService:
    BASE_URL = "https://leetcode-stats-api.herokuapp.com"

    def fetch_stats(self, username: str) -> Dict[str, Any]:
        """
        Fetches LeetCode stats for a given username.
        Uses a public wrapper API. Falls back to mock data if API fails.
        """
        if not username:
            return {"error": "No username provided"}

        try:
            # Try fetching from real API
            response = requests.get(f"{self.BASE_URL}/{username}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "error":
                     return self._get_mock_stats(username, error="User not found")
                return {
                    "username": username,
                    "total_solved": data.get("totalSolved", 0),
                    "easy_solved": data.get("easySolved", 0),
                    "medium_solved": data.get("mediumSolved", 0),
                    "hard_solved": data.get("hardSolved", 0),
                    "ranking": data.get("ranking", "N/A"),
                    "acceptance_rate": data.get("acceptanceRate", 0),
                }
        except Exception as e:
            print(f"LeetCode API Error: {e}. Using mock data.")
        
        # Fallback to mock data for demo stability
        return self._get_mock_stats(username)

    def _get_mock_stats(self, username: str, error: Optional[str] = None) -> Dict[str, Any]:
        if error:
            return {"username": username, "error": error}
            
        # Deterministic mock stats based on username length to simulate variety
        seed = len(username)
        return {
            "username": username,
            "total_solved": 150 + (seed * 10),
            "easy_solved": 50 + (seed * 5),
            "medium_solved": 80 + (seed * 3),
            "hard_solved": 20 + (seed * 2),
            "ranking": 100000 - (seed * 1000),
            "acceptance_rate": 65.5,
            "is_mock": True
        }
