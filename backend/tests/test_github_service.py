import requests

from app.services import github as github_module
from app.services.github import GitHubService


class _FakeSession:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.trust_env = False

    def get(self, url, headers=None, timeout=None):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _response(status_code=200, headers=None, body=b"{}"):
    response = requests.Response()
    response.status_code = status_code
    response.headers.update(headers or {})
    response._content = body
    response.url = "https://api.github.com/test"
    return response


def test_github_request_retries_connection_errors(monkeypatch):
    sleeps = []
    monkeypatch.setattr(github_module.time, "sleep", lambda seconds: sleeps.append(seconds))

    service = GitHubService()
    service._session = _FakeSession([
        requests.exceptions.ConnectionError("remote disconnected"),
        _response(200),
    ])

    response = service._request("https://api.github.com/test")

    assert response.status_code == 200
    assert service._session.calls == 2
    assert sleeps == [2]


def test_github_request_retries_5xx_with_backoff(monkeypatch):
    sleeps = []
    monkeypatch.setattr(github_module.time, "sleep", lambda seconds: sleeps.append(seconds))

    service = GitHubService()
    service._session = _FakeSession([
        _response(503),
        _response(502),
        _response(200),
    ])

    response = service._request("https://api.github.com/test")

    assert response.status_code == 200
    assert service._session.calls == 3
    assert sleeps == [2, 4]
