import pytest

from app.services.leetcode import LeetCodeService


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


@pytest.mark.unit
def test_leetcode_service_fetches_real_graphql_shape(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["variables"] = kwargs["json"]["variables"]
        return _FakeResponse({
            "data": {
                "matchedUser": {
                    "username": "candidate-dev",
                    "submitStatsGlobal": {
                        "acSubmissionNum": [
                            {"difficulty": "All", "count": 120, "submissions": 240},
                            {"difficulty": "Easy", "count": 60, "submissions": 90},
                            {"difficulty": "Medium", "count": 50, "submissions": 120},
                            {"difficulty": "Hard", "count": 10, "submissions": 30},
                        ]
                    },
                    "profile": {"ranking": 12345},
                }
            }
        })

    monkeypatch.setattr("app.services.leetcode.requests.post", fake_post)

    stats = LeetCodeService().fetch_stats("https://leetcode.com/u/candidate-dev/")

    assert captured["url"] == LeetCodeService.GRAPHQL_URL
    assert captured["variables"]["username"] == "candidate-dev"
    assert stats["total_solved"] == 120
    assert stats["easy_solved"] == 60
    assert stats["medium_solved"] == 50
    assert stats["hard_solved"] == 10
    assert stats["acceptance_rate"] == 50.0
    assert stats["is_mock"] is False


@pytest.mark.unit
def test_leetcode_service_never_returns_mock_on_failure(monkeypatch):
    def fake_post(*args, **kwargs):
        raise TimeoutError("network down")

    monkeypatch.setattr("app.services.leetcode.requests.post", fake_post)

    stats = LeetCodeService().fetch_stats("missing-user")

    assert stats["username"] == "missing-user"
    assert stats["error"] == "LeetCode stats unavailable"
    assert "total_solved" not in stats
